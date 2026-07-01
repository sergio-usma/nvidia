<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Investiga como implementar esto en una guía paso a paso que inicie con la descripción clara del problema y la solución a implementar:

"""

# Arquitectura de Arranque Cero Confianza: Guía para un Jetson Orin AGX Libre de Servicios Residuales

## Análisis de Mecanismos de Arranque Automático de Herramientas de Inferencia Local

El objetivo de establecer un entorno de arranque mínimo y controlado en un NVIDIA Jetson Orin AGX con JetPack 7.2 requiere una comprensión profunda de cómo las herramientas de inferencia local de grandes modelos de lenguaje (LLM) como Ollama, vLLM y llama.cpp interactúan con el sistema operativo subyacente. Estas herramientas, diseñadas para la facilidad de uso y la rápida puesta en marcha, a menudo incorporan funcionalidades automáticas de inicio que entran en conflicto directo con los requisitos de un entorno minimalista y predecible [[111,162]]. El problema central no es solo el consumo de recursos, sino la introducción de variables imprevistas en el estado del sistema antes de que el usuario pueda implementar sus pipelines de trabajo, lo que lleva a errores de desbordamiento de memoria (OOM) debido a la limitada memoria unificada del dispositivo [[32]]. Un análisis detallado de cada herramienta revela patrones distintos pero igualmente problemáticos.

Ollama se destaca como la herramienta más proactiva y potencialmente disruptiva para un arranque limpio. Su instalador oficial, que se ejecuta mediante un único comando de shell (`curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh`), está programado para realizar varias acciones automáticas, una de las cuales es la creación e activación de un servicio `systemd` [[3,56]]. Este servicio, típicamente ubicado en `/etc/systemd/system/ollama.service`, está diseñado para iniciar el servidor de Ollama (`ollama serve`) en segundo plano y mantenerlo activo a través de reinicios del sistema [[108]]. Esta acción ocurre de forma predeterminada, sin solicitar confirmación explícita al usuario para un escenario de producción o desarrollo minimalista. La documentación comunitaria refuerza este comportamiento, ya que describe métodos para crear manualmente dicho servicio si el instalador falla, lo que indica que es un componente fundamental de su arquitectura [[4]]. Además, es crucial entender que Ollama utiliza llama.cpp como su motor de inferencia subyacente, lo que significa que la instalación de Ollama implica indirectamente la presencia de componentes y bibliotecas de llama.cpp en el sistema [[3]]. Aunque existe un informe de error indicando que una versión específica de Ollama podría no ser compatible con JetPack 7.2, sugiriendo que podría no funcionar correctamente, el acto de instalación en sí mismo sigue siendo un riesgo significativo [[62]].

En contraste, vLLM adopta un enfoque diferente. Generalmente se instala a través de `pip` (`pip install vllm`) y se ejecuta principalmente a través de una interfaz de línea de comandos o sirviendo modelos a través de una API compatible con OpenAI [[17,112]]. Las fuentes disponibles sugieren que vLLM no configura servicios de arranque de forma predeterminada [[61]]. De hecho, la existencia de discusiones en foros de desarrolladores sobre cómo ejecutar vLLM como un servicio en JetPack 7.2 indica que esta funcionalidad no está integrada y requiere una configuración manual explícita por parte del usuario [[61]]. Este comportamiento lo convierte en una opción inherentemente más segura desde la perspectiva de un arranque limpio, ya que no introduce artefactos de arranque automáticos. Sin embargo, esto también implica que el usuario tiene una mayor responsabilidad en la gestión de su ciclo de vida, ya que cualquier intento de automatización debe ser realizado de manera consciente y deliberada.

La situación con llama.cpp es similar a la de vLLM en el sentido de que la herramienta principal se presenta como una utilidad de línea de comandos para la inferencia directa [[22,38]]. No obstante, la flexibilidad de llama.cpp ha dado lugar a una ecología diversa de capas de abstracción y wrappers, como `llama-server` o `llama-swap`, que pueden añadir complejidad [[36,93]]. Estos wrappers a menudo se gestionan a través de `systemd`. Es común encontrar configuraciones donde un wrapper se instala como un servicio `systemd` de nivel de usuario, localizado en `~/.config/systemd/user/` [[36,37]]. Esto significa que la responsabilidad recae casi por completo en el usuario final. Si un script de instalación o un procedimiento manual crea accidentalmente tal servicio, se romperá el estado limpio deseado. Por lo tanto, aunque llama.cpp por sí solo es benigno, su ecosistema de herramientas puede introducir puntos de arranque automático no deseados si no se gestiona con cuidado.

La siguiente tabla resume los patrones de arranque de cada herramienta, basándose en la información extraída:


| Característica | Ollama | vLLM | llama.cpp |
| :-- | :-- | :-- | :-- |
| Método de Instalación Predominante | Script de instalación (`install.sh`) [[20]] | `pip install` [[17]] | Compilación desde código fuente [[38]] |
| Gestión de Arranque por Defecto | Crea un servicio `systemd` (`/etc/systemd/system/ollama.service`) [[3,56]] | No hay un servicio de arranque predeterminado [[61]] | No hay un servicio de arranque predeterminado [[38]] |
| Dependencia Subyacente | Utiliza llama.cpp como motor de inferencia [[3]] | Motor propio; no depende de llama.cpp [[19]] | Motor base; puede ser utilizado por otras herramientas como Ollama [[55]] |
| Complejidad de Ecosistema | Moderada (proporciona su propio daemon) [[58]] | Baja (principalmente CLI/API) [[112]] | Alta (muchos wrappers y scripts de lanzamiento personalizados) [[36,163]] |
| Riesgo de Arranque No Deseado | Alto (comportamiento predeterminado) | Muy Bajo (requiere configuración manual) | Variable (depende de la implementación del usuario) |

Este análisis demuestra que el riesgo de introducir servicios no deseadados en el arranque proviene principalmente de Ollama debido a su diseño de instalación automática. Para cumplir el objetivo del usuario, es imperativo implementar una estrategia de hardening del sistema que neutralice estos comportamientos predeterminados y establezca un estado inicial limpio y controlado que permanezca intacto incluso después de la instalación posterior de estas herramientas.

## Hardening del Sistema: Configuración Inicial para un Entorno Minimalista

Para construir un entorno de arranque verdaderamente mínimo y limpio en el NVIDIA Jetson Orin AGX, es fundamental llevar a cabo una serie de medidas de hardening sistemáticas desde el principio. Estas acciones no solo eliminan servicios innecesarios, sino que también modifican las configuraciones predeterminadas del sistema para que el estado "limpio" se vuelva el comportamiento por defecto. Este proceso se centra en el control total del gestor de servicios `systemd`, que es el núcleo de la administración de procesos en Ubuntu 24.04 LTS, la distribución soportada por JetPack 7.2 [[6,45]]. El primer y más crucial paso es eliminar la carga de cualquier entorno de escritorio gráfico, ya que su activación inicia una cascada de servicios que consumen recursos valiosos de memoria unificada. La forma más efectiva de lograr esto en Ubuntu es cambiando el destino de ejecución predeterminado del sistema a `multi-user.target`.

El cambio a `multi-user.target` es el pilar de la configuración minimalista. Este destino representa un entorno de Linux multiusuario en modo texto, sin un servidor X ni un gestor de sesiones gráficas. Al ejecutar el comando `sudo systemctl set-default multi-user.target`, se instruye al sistema a no iniciar el gestor de display gráfico (GDM en Ubuntu) por defecto [[1]]. Este es quizás el paso más importante para garantizar que el sistema arranque en un estado lo más parecido posible a un servidor de propósito general. Es vital notar que en versiones recientes de Ubuntu, como la 24.04, el gestor de displays GDM puede estar estrechamente vinculado a la unidad `graphical.target`. Por lo tanto, cambiar el destino predeterminado es el método correcto y robusto para deshabilitar el entorno gráfico sin necesidad de mascar o forzar el cese de servicios individuales, que podría no ser suficiente [[1]]. Tras ejecutar este comando y reiniciar el sistema, se puede verificar que el entorno gráfico no se ha iniciado consultando el estado del servicio del gestor de display, esperando una salida que indique que es inactivo [[1]].

Una vez establecido un entorno sin cabeza, el siguiente paso es auditar y gestionar meticulosamente todos los servicios `systemd` que están habilitados para el arranque. La instalación de herramientas como Ollama puede haber dejado atrás archivos de servicio, como `/etc/systemd/system/ollama.service` [[108]]. Es imperativo identificar y deshabilitar todos estos servicios no deseados. Se puede listar todos los servicios y su estado de habilitación con el comando `systemctl list-unit-files --type=service`. Para filtrar los resultados y buscar servicios sospechosos relacionados con LLMs, se pueden usar expresiones regulares como `grep -E "(ollama|vllm|llama)"`. Una vez identificado un servicio, por ejemplo, `ollama`, se debe deshabilitar permanentemente con el comando `sudo systemctl disable ollama` [[34]]. Este comando no solo desvincula el servicio del objetivo de arranque, sino que también, en muchos casos, puede eliminar el archivo unitario si fue creado por un paquete `dpkg`. Para una limpieza completa, si el archivo unitario persiste, debe ser eliminado manualmente con `sudo rm /etc/systemd/system/ollama.service` antes de volver a ejecutar `systemctl disable` [[156]]. Este proceso de auditoría y deshabilitación debe extenderse a cualquier otro servicio que no sea estrictamente indispensable para el funcionamiento básico del sistema y el acceso remoto.

Finalmente, el control sobre los contenedores Docker es una pieza clave de la estrategia de hardening. Muchas implementaciones de LLM se empaquetan y ejecutan dentro de contenedores, y estos pueden tener políticas de reinicio configuradas que contravienen el objetivo de un arranque limpio. Docker proporciona mecanismos para controlar el comportamiento de los contenedores en el arranque. Por defecto, algunos contenedores pueden ser creados con una política de reinicio de `always`, lo que significa que Docker tratará de reiniciarlos automáticamente si se detienen o si el demonio de Docker se reinicia [[109]]. Para neutralizar este comportamiento, es necesario actualizar el contenedor para que use una política de reinicio que lo desactive. El comando `docker update --restart=no $(docker ps -a -q)` desactivará el reinicio automático para todos los contenedores existentes [[35]]. Para un control más granular, se puede aplicar este cambio a un contenedor específico: `docker update --restart=no <nombre_del_contenedor>`. Además, para una seguridad adicional, se puede deshabilitar el propio demonio de Docker para que no se inicie en el arranque del sistema, lo que obligaría al usuario a iniciar explícitamente tanto el daemon como los contenedores que necesita en un momento determinado. Esto se logra con `sudo systemctl disable docker`. Al combinar estos tres niveles de control —el destino predeterminado de `systemd`, la deshabilitación de servicios individuales y el manejo estricto de las políticas de reinicio de Docker— se crea un sistema robusto y predecible, libre de las influencias externas que podrían comprometer el estado limpio deseado.

## Implementación de Acceso Remoto Seguro y Eficiente (SSH y NoMachine)

Para un sistema configurado en modo headless, la capacidad de acceder y gestionarlo de forma remota es no negociable. El objetivo del usuario especifica dos herramientas indispensables: SSH para la gestión por línea de comandos y NoMachine para la visualización de interfaces gráficas cuando sea necesario. La implementación de estas herramientas debe ser precisa y resiliente, especialmente en el caso de NoMachine, que presenta desafíos únicos en un entorno sin monitor físico. Un aspecto crítico para ambas herramientas es la configuración de una dirección IP estática en la red. Sin una IP fija, la conectividad podría interrumpirse después de cada reinicio del sistema, anulando los beneficios de un acceso remoto fiable [[1]].

La configuración de SSH es un procedimiento estándar. En la mayoría de las instalaciones de JetPack, el paquete `openssh-server` suele estar presente o puede ser instalado fácilmente con el comando `sudo apt install openssh-server` [[150]]. Una vez instalado, el servicio `ssh` se iniciará automáticamente si no se ha deshabilitado. Para asegurar que siempre se ejecute en un entorno minimalista, es recomendable verificar su estado y habilitarlo explícitamente: `sudo systemctl enable ssh` y `sudo systemctl start ssh`. La configuración de la IP estática se realiza típicamente a través de los archivos de configuración de Netplan, ubicados en `/etc/netplan/`. Creando o editando un archivo `.yaml` en este directorio, se puede definir la configuración de red estática para la interfaz de red deseada, asegurando que el dispositivo mantenga la misma dirección IP en la red local tras cada reinicio [[1]].

La configuración de NoMachine en un Jetson Orin en modo headless es mucho más compleja y requiere una atención especial a los detalles del subsistema de video y el gestor de displays. NoMachine es una solución popular en la comunidad Jetson por su rendimiento y facilidad de uso, pero su funcionamiento depende de un servidor X11 virtual [[25]]. Aquí es donde surgen los conflictos. Ubuntu 24.04, junto con JetPack 7.2, utiliza GNOME como entorno de escritorio por defecto, y su compositor, Mutter, depende fuertemente de características avanzadas de aceleración de GPU (DRI3) [[1]]. El servidor de visualización virtual que NoMachine emula no expone adecuadamente estas características, lo que resulta en una pantalla negra o solo una imagen de fondo cuando se intenta conectar [[1]]. La solución a este problema es doble: primero, es recomendable utilizar XFCE4 como entorno de escritorio preferido para NoMachine, ya que es menos exigente que GNOME [[1]]. Segundo, y más importante para un arranque limpio, es forzar al sistema a utilizar el protocolo X11 en lugar de Wayland.

Wayland es el sucesor moderno de X11, pero su arquitectura no es compatible con los flujos de trabajo de escritorio remoto tradicionales que dependen de servidores X virtuales. Por lo tanto, es fundamental deshabilitar Wayland en favor de X11. Esto se logra editando el archivo de configuración del gestor de displays gdm3 en `/etc/gdm3/custom.conf` y descomentando o añadiendo la línea `WaylandEnable=false` dentro de la sección `[daemon]` [[1]]. Este simple cambio es crucial para que cualquier servidor X, incluido el de NoMachine, pueda funcionar correctamente en un entorno headless. Además, para proporcionar un backend de video funcional sin hardware físico, es necesario instalar el driver de video dummy (`xserver-xorg-video-dummy`) [[1]]. Con el driver instalado, se debe crear una configuración Xorg personalizada en `/etc/X11/xorg.conf.d/30-tegra-headless.conf`. Este archivo define una pantalla virtual utilizando el controlador de GPU Tegra del Jetson, estableciendo una resolución y profundidad de color específicas (por ejemplo, 1920x1080) que será visible a través de NoMachine [[1]].

Finalmente, para garantizar que NoMachine se inicie y se mantenga en ejecución de manera fiable, debe ser gestionado a través de un servicio `systemd` dedicado. Crear un archivo unitario en `/etc/systemd/system/nomachine-headless.service` permite encapsular la lógica de inicio del servidor de NoMachine. Una configuración eficaz para este servicio sería usar `Type=oneshot` con `RemainAfterExit=yes`. Esto le dice a `systemd` que ejecute el comando `nxserver --restart` una vez durante el arranque, y aunque el comando termine, el tipo de servicio seguirá considerándose activo, permitiendo que el servidor de NoMachine continúe ejecutándose como un demonio en segundo plano [[1]]. Después de crear el archivo de servicio, se debe cargar la nueva configuración con `sudo systemctl daemon-reload`, habilitarlo para que se inicie en el arranque con `sudo systemctl enable nomachine-headless.service`, y finalmente, iniciar el servicio manualmente con `sudo systemctl start nomachine-headless.service`. Este enfoque estructurado y basado en `systemd` proporciona un control total y persistente sobre el servicio de escritorio remoto, completando así la pila de acceso remoto indispensable para el sistema minimalista.

## Estrategias de Contención y Prevención de Servicios Persistentes

Para satisfacer el requisito de que el sistema permanezca limpio incluso después de reinstalar herramientas de inferencia como Ollama, vLLM o llama.cpp, es necesario ir más allá de la simple eliminación de servicios existentes. La estrategia debe ser proactiva, enfocada en contener los mecanismos de arranque automático que estas herramientas pueden intentar registrar y en establecer una configuración de sistema que haga que el estado limpio sea intrínsecamente difícil de alterar. Esto implica una combinación de hardening del sistema, monitoreo de cambios y una mentalidad de "no confiar, pero verificar".

La primera línea de defensa es el hardening exhaustivo del sistema, como se detalló anteriormente. Establecer el `default.target` en `multi-user.target`, deshabilitar todos los servicios no esenciales y gestionar rigurosamente los servicios de `systemd` crea una base sólida. Sin embargo, las herramientas de software, especialmente aquellas que se instalan a través de scripts de shell, tienen la capacidad de modificar estas configuraciones. Ollama, por ejemplo, tiene un instalador que intencionadamente crea un servicio `systemd` [[3,56]]. Por lo tanto, la estrategia de contención debe incluir un paso post-instalación sistemático. Tras la instalación de cualquiera de estas herramientas, es imperativo volver a auditar el estado de los servicios `systemd`. Se debe ejecutar `systemctl list-unit-files --type=service` y buscar cualquier nuevo servicio recién creado que corresponda a la herramienta recientemente instalada. Si se encuentra uno, debe ser deshabilitado y, si es posible, eliminado [[156]]. Este proceso convierte la instalación de la herramienta en un evento de "activación" en lugar de "automatización". El usuario instala la herramienta, pero luego debe tomar una acción explícita y consciente para habilitar su arranque automático, si lo desea.

Una segunda estrategia consiste en gestionar los permisos y la estructura del sistema de archivos para dificultar las modificaciones no autorizadas. Aunque esto es más avanzado, se puede considerar aislar las instalaciones de LLM en espacios de nombres de contenedores o mediante sandboxing a nivel de servicio, aprovechando las capacidades de `systemd` para asignar permisos y recursos específicos a cada servicio [[34]]. Más sencillamente, se puede auditar y limpiar regularmente los directorios de inicio del usuario, como `~/.config/systemd/user/`, donde los usuarios pueden crear servicios de nivel de usuario que se inician con su sesión [[36,37]]. Antes de reinstalar una herramienta de LLM, es prudente revisar estos directorios para eliminar cualquier servicio residual relacionado. Del mismo modo, los archivos de perfil del usuario como `~/.bashrc` o `~/.profile` deben ser revisados en busca de líneas que lancen procesos en segundo plano, ya que son otros vectores comunes para el arranque automático [[148]].

Además, el control sobre Docker es una medida de contención crítica. Como se mencionó, se debe configurar el demonio de Docker para que no se inicie en el arranque del sistema (`sudo systemctl disable docker`) [[35]]. Esto proporciona un punto de control central. Cuando el usuario necesite ejecutar un contenedor de LLM, deberá iniciar explícitamente el demonio de Docker (`sudo systemctl start docker`) y luego lanzar el contenedor con una política de reinicio explícitamente definida, preferiblemente `--restart=no` para evitar reinicios automáticos posteriores [[35,109]]. Este enfoque obliga al usuario a pensar en términos de estados: el sistema está "apagado" (daemon de Docker inactivo) o el usuario activa explícitamente el servicio y el contenedor que necesita. Esto elimina la posibilidad de que un contenedor olvidado o mal configurado consuma recursos en segundo plano.

Finalmente, aunque menos probable en una instalación moderna de Ubuntu 24.04, es una buena práctica de hardening verificar la existencia y el contenido de archivos de arranque heredados como `/etc/rc.local` [[148]]. Scripts colocados en este archivo se ejecutan con privilegios de root durante el proceso de arranque. Asegurarse de que este archivo esté vacío o bien documentado ayuda a cerrar cualquier hueco de seguridad histórico. En conjunto, estas estrategias de contención transforman la configuración del sistema de una simple lista de tareas a un ecosistema de control. No se trata solo de limpiar después de que algo suceda, sino de construir un sistema donde el comportamiento predeterminado sea intrínsecamente seguro y limpio, haciendo que cualquier intento de introducir servicios persistentes sea una tarea deliberada y detectable por parte del administrador del sistema.

## Guía de Implementación Paso a Paso para un Estado Limpio y Persistente

Esta sección consolida el análisis previo en una guía de implementación práctica, reproducible y robusta. El objetivo es proporcionar una secuencia de comandos y configuraciones claras que lleven desde una instalación base de JetPack 7.2 hasta un sistema NVIDIA Jetson Orin AGX 64GB completamente preparado para cargas de trabajo dinámicas, con un arranque mínimo, seguro y libre de interferencias de herramientas de LLM. La guía asume que se parte de un sistema fresco para maximizar la limpieza inicial.

**Paso 0: Preparación del Entorno Base**

Antes de comenzar, es altamente recomendable realizar una instalación limpia de JetPack 7.2. Si se está actualizando desde una versión anterior, se debe realizar un borrado total del dispositivo para evitar la contaminación de archivos y configuraciones residuales. El comando `sudo ./flash.sh --erase-all jetson-agx-orin-devkit internal` es el método oficial para borrar todo el contenido del medio de almacenamiento antes de escribir una nueva imagen del sistema operativo [[13]].

Una vez que el sistema está instalado y accesible, el primer paso es actualizar todos los paquetes del sistema para asegurar que se dispone de las últimas versiones de seguridad y compatibilidad:

```bash
sudo apt update && sudo apt upgrade -y
```

Es importante señalar que las actualizaciones del kernel, como la transición a la versión 6.8 en Ubuntu 24.04, pueden introducir problemas de arranque o compatibilidad con los controladores de NVIDIA [[85,86,87]]. Por lo tanto, después de una actualización mayor del sistema, es crucial verificar que el sistema se reinicie correctamente y que los controladores de NVIDIA funcionan como se espera.

**Paso 1: Configuración Inicial Minimalista y de Red**

Este paso establece la base del entorno headless y configure los servicios indispensables.

1. **Cambiar a modo multi-usuario:** Deshabilita el arranque del entorno gráfico para liberar recursos. Ejecuta el siguiente comando y reinicia el sistema:

```bash
sudo systemctl set-default multi-user.target
```

Después del reinicio, verifica que el gestor de displays no se está ejecutando: `systemctl is-active gdm3`.
2. **Instalar y configurar SSH:** Asegúrate de que el servidor SSH esté instalado y habilitado para el arranque:

```bash
sudo apt install -y openssh-server
sudo systemctl enable ssh
```

Configura una IP estática editando el archivo de configuración de Netplan en `/etc/netplan/`. Por ejemplo, crea o edita `/etc/netplan/01-netcfg.yaml`:

```yaml
network:
  version: 2
  ethernets:
    etherneta:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Aplica la configuración con `sudo netplan apply`.
3. **Instalar y configurar NoMachine para modo sin cabeza:**
    * Descarga e instala el paquete de NoMachine para ARM64 desde el sitio web oficial.
    * Edita el archivo de configuración de GDM para forzar el uso de X11: `sudo nano /etc/gdm3/custom.conf`. Descomenta o añade la línea `WaylandEnable=false`.
    * Instala el controlador de video dummy: `sudo apt install -y xserver-xorg-video-dummy`.
    * Crea la configuración Xorg para la pantalla virtual: `sudo nano /etc/X11/xorg.conf.d/30-tegra-headless.conf`. Pega el siguiente contenido, ajustando la resolución según sea necesario:

```
Section "Device"
    Identifier "DummyDevice"
    Driver "dummy"
    Option "IgnoreEDID", "true"
    VideoRam 256000
EndSection

Section "Screen"
    Identifier "DummyScreen"
    Device "DummyDevice"
    DefaultDepth 24
    SubSection "Display"
        Viewport 0 0
        Depth 24
        Virtual 1920 1080
        Colors 24-bit
    EndSubSection
EndSection
```


**Paso 2: Hardenning de `systemd` y Contenedores**

Estos pasos aseguran que ningún servicio no deseado pueda iniciar automáticamente.

1. **Deshabilitar servicios conocidos:** Verifica y deshabilita cualquier servicio de LLM que pudiera haber sido creado por un instalador previo. Si existe un servicio de Ollama, ejecuta:

```bash
sudo systemctl stop ollama  # Si está activo
sudo systemctl disable ollama
sudo rm /etc/systemd/system/ollama.service 2>/dev/null || true
```

Repite este proceso para cualquier otro servicio sospechoso.
2. **Controlar el demonio de Docker:** Para obtener el máximo control, deshabilita el arranque del demonio de Docker:

```bash
sudo systemctl disable docker
```

Esto significa que el usuario deberá iniciar Docker explícitamente cuando sea necesario.

**Paso 3: Implementación de Herramientas de LLM (Proceso de "Activación")**

En este punto, el sistema está completamente limpio. La instalación de vLLM, Ollama o llama.cpp puede realizarse, pero con la conciencia de que pueden intentar modificar el sistema.

1. **Instalar la herramienta de LLM:** Sigue los procedimientos de instalación oficiales para tu herramienta preferida (vLLM, Ollama, llama.cpp). Por ejemplo, para Ollama, ejecuta el script de instalación oficial.
2. **Auditar post-instalación:** Inmediatamente después de la instalación, vuelve a ejecutar la auditoría de servicios `systemd` para identificar cualquier nuevo servicio creado por el instalador.
3. **Crear un servicio personalizado (si es necesario):** Si la herramienta no se inicia automáticamente (lo cual es deseable), el usuario debe crear su propio servicio `systemd` para gestionarla de forma explícita cuando la necesite. Por ejemplo, para un servidor llama.cpp personalizado, se podría crear un servicio en `/etc/systemd/system/my-llm-server.service` que ejecute el binario correspondiente con los parámetros deseados. Habilitar este servicio (`sudo systemctl enable my-llm-server.service`) es la única forma de que se inicie, dando al usuario un control total sobre qué servicios se ejecutan en el sistema.

Siguiendo esta guía, el usuario no solo logra un estado de arranque limpio, sino que también establece un paradigma de gestión de servicios donde la automatización no deseada es neutralizada y la ejecución de servicios adicionales se convierte en una acción deliberada y controlada. Esta arquitectura garantiza la disponibilidad de recursos de memoria unificada para las cargas de trabajo de IA y previene los errores de desbordamiento de memoria, cumpliendo así con todos los objetivos planteados.
"""

Aquí tienes una **guía paso a paso** para implementar una arquitectura de arranque “cero confianza” en un Jetson Orin AGX con JetPack 7.2, empezando por la descripción clara del problema y la solución. El objetivo es que el sistema arranque en un estado mínimo, sin servicios residuales, y que cualquier herramienta de inferencia local se ejecute solo cuando tú la actives explícitamente. Ollama sí tiende a crear un servicio `systemd` de arranque automático al instalarse, mientras que vLLM y `llama.cpp` no suelen hacerlo por defecto; además, `systemctl set-default multi-user.target` es la forma estándar de arrancar en modo texto y evitar el entorno gráfico por defecto.[^1_1][^1_2][^1_3]

## Problema y solución

El problema central es que un Jetson con memoria unificada limitada puede perder recursos valiosos si arranca con GUI, demonios innecesarios o contenedores configurados para reiniciarse solos. Eso introduce variabilidad antes de que tú despliegues tus flujos de trabajo, y en un equipo de IA embebida esa variabilidad se traduce fácilmente en presión de memoria y comportamiento impredecible.[^1_3][^1_4][^1_5]

La solución es construir el sistema en capas: arrancar en `multi-user.target`, dejar solo SSH y NoMachine como accesos remotos controlados, deshabilitar cualquier servicio de LLM creado automáticamente, y forzar que Docker no levante contenedores sin permiso explícito. Para NoMachine en modo headless, la documentación de Jetson/virtual display indica que conviene usar una pantalla virtual y mantener el servidor gráfico en modo compatible con acceso remoto, típicamente con X11/virtual display en lugar de depender solo de una sesión gráfica completa.[^1_6][^1_7]

## Arquitectura objetivo

| Capa | Estado deseado | Motivo |
| :-- | :-- | :-- |
| Arranque del sistema | `multi-user.target` | Evita GUI y reduce consumo base [^1_3][^1_8]. |
| Acceso remoto | SSH activo, IP estática | Administración confiable sin monitor físico [^1_4][^1_7]. |
| Escritorio remoto | NoMachine con display virtual | Solo cuando necesites GUI remota [^1_6][^1_7]. |
| LLM local | Sin autoarranque | Evita servicios residuales como `ollama.service` [^1_1]. |
| Contenedores | `--restart=no` y Docker deshabilitado por defecto | Impide reinicios automáticos no deseados [^1_9][^1_5][^1_10]. |

## Implementación base

1. Instala JetPack 7.2 en limpio y actualiza el sistema.
```bash
sudo apt update && sudo apt upgrade -y
```

JetPack 7.2 para AGX Orin está basado en el stack de Jetson Linux r39.2 y Ubuntu 24.04 en el contexto reciente del ecosistema Jetson, así que conviene partir de una instalación limpia para evitar residuos previos.[^1_11][^1_3]

2. Cambia el arranque por defecto a modo texto.
```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

Ese cambio hace que el sistema arranque sin entorno gráfico por defecto, que es exactamente lo que buscas para un entorno minimalista.[^1_8][^1_3]

3. Verifica el estado tras reiniciar.
```bash
systemctl get-default
systemctl is-active gdm3
```

Si todo quedó bien, el objetivo por defecto debe ser `multi-user.target` y el gestor gráfico no debería estar activo al arranque.[^1_3][^1_8]

## Acceso remoto seguro

1. Instala y habilita SSH.
```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

SSH es la vía principal para administrar el Jetson sin depender de la GUI.[^1_4][^1_7]

2. Configura IP estática con Netplan.
Crea o edita un archivo en `/etc/netplan/*.yaml` y define una dirección fija para que NoMachine y SSH no cambien de IP tras reiniciar. La necesidad de conectividad estable en headless está alineada con las guías de operación remota en Jetson.[^1_7][^1_4]
3. Instala NoMachine solo si necesitas GUI remota.
En Jetson headless, la clave es que NoMachine dependa de una pantalla virtual y no de una sesión gráfica completa siempre activa; las guías de display virtual en Jetson muestran precisamente ese enfoque. Si observas pantallas negras o fallos de sesión, la solución habitual es forzar X11/virtual display y no Wayland/GNOME puro.[^1_6][^1_7]

## Blindaje de servicios

1. Audita servicios habilitados.
```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
```

Ollama documenta explícitamente un servicio `ollama.service` en `/etc/systemd/system/ollama.service`, con `Restart=always`, lo que confirma que puede dejar persistencia si lo instalas sin control.[^1_1]

2. Deshabilita y elimina cualquier servicio residual.
```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

La documentación oficial de Ollama muestra la creación y eliminación de ese servicio, así que esta limpieza es coherente con su modelo de instalación.[^1_1]

3. No asumas que vLLM o `llama.cpp` crean servicios por sí solos.
vLLM se instala con `pip` y su documentación se centra en ejecución por CLI o servidor API, no en autoarranque del sistema; `llama.cpp` también se presenta como una utilidad de inferencia/servidor que el usuario levanta explícitamente, no como un daemon persistente por defecto.[^1_2]

## Control de Docker

1. Deshabilita Docker al arranque si quieres control total.
```bash
sudo systemctl disable docker
```

2. Si ya existen contenedores, quítales el reinicio automático.
```bash
docker update --restart=no $(docker ps -a -q)
```

La política `always` o `unless-stopped` puede relanzar contenedores al reiniciar Docker o el sistema, así que conviene neutralizarla si tu prioridad es un arranque limpio.[^1_9][^1_5][^1_10]

3. Si un contenedor debe vivir, hazlo manualmente y con política explícita.
Eso convierte la ejecución en una decisión consciente, no en un efecto colateral de instalar herramientas de IA o reiniciar el equipo.[^1_5][^1_9]

## Procedimiento recomendado

1. Instala JetPack 7.2 en limpio.
2. Cambia a `multi-user.target`.
3. Configura SSH e IP estática.
4. Instala NoMachine solo con display virtual si necesitas GUI remota.
5. Deshabilita Docker por defecto.
6. Instala Ollama, vLLM o `llama.cpp` solo cuando lo requieras.
7. Inmediatamente después, audita `systemd` y elimina cualquier servicio residual.
8. Mantén un script de limpieza post-instalación para repetir el control cada vez que reinstales herramientas.

Este enfoque convierte el sistema en una plataforma de **activación explícita**: nada arranca solo, nada persiste sin que tú lo permitas, y cualquier servicio nuevo queda bajo revisión antes de volverse parte del boot.[^1_2][^1_3][^1_1]

## Script mínimo sugerido

```bash
sudo systemctl set-default multi-user.target
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo systemctl disable docker
sudo systemctl daemon-reload
```

Después de instalar cualquier herramienta de inferencia, repite:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
docker update --restart=no $(docker ps -a -q) 2>/dev/null || true
```

Puedo convertir esto ahora en una **guía técnica formal estilo manual de implementación**, con secciones, comandos validados y checklist de verificación final.
<span style="display:none">[^1_12][^1_13][^1_14][^1_15][^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30]</span>

<div align="center">⁂</div>

[^1_1]: https://docs.ollama.com/linux

[^1_2]: https://docs.vllm.ai/en/v0.5.0/getting_started/installation.html

[^1_3]: http://somebooks.es/iniciar-ubuntu-24-04-lts-sin-interfaz-grafica-parte-ii/

[^1_4]: https://forums.developer.nvidia.com/t/headless-mode-on-nvidia-jetson-agx-orin-64gb-with-jetpack-7-2/374718

[^1_5]: https://stackoverflow.com/questions/37599128/docker-how-do-you-disable-auto-restart-on-a-container

[^1_6]: https://www.stereolabs.com/docs/development/zed-sdk/virtual-display

[^1_7]: https://forums.developer.nvidia.com/t/problem-while-attempting-use-gui-in-headless-mode/167307

[^1_8]: https://docs.redhat.com/es/documentation/red_hat_enterprise_linux/8/html/configuring_basic_system_settings/changing-the-default-target_working-with-systemd-targets

[^1_9]: https://oneuptime.com/blog/post/2026-01-16-docker-restart-policies/view

[^1_10]: https://github.com/moby/moby/issues/10032

[^1_11]: https://forums.developer.nvidia.com/t/jetpack-7-2-jetson-linux-r39-2-on-jetson-agx-orin-developer-kit-getting-started-and-feedback-thread/372156

[^1_12]: https://zenn.dev/nooop/articles/785b7c511f991b?locale=en

[^1_13]: https://www.linuxmaster.jp/linux_skill/2026/06/ollama-systemd-service-autostart.html

[^1_14]: https://docs.stereolabs.com/docs/development/zed-sdk/linux/work-with-nvidia-jetson/virtual-display-headless-mode

[^1_15]: https://github.com/ollama/ollama/blob/main/scripts/install.sh

[^1_16]: https://github.com/ollama/ollama/pull/5601/files

[^1_17]: https://github.com/ollama/ollama/pull/5601/commits

[^1_18]: https://docs.ollama.com/faq

[^1_19]: https://github.com/ollama/ollama/pull/5601

[^1_20]: https://computingforgeeks.com/install-vllm-linux-production/

[^1_21]: https://liujiacai.net/blog/2026/02/18/headless-ubuntu-pitfalls/

[^1_22]: https://oneuptime.com/blog/post/2026-03-02-how-to-install-and-configure-vllm-on-ubuntu/view

[^1_23]: https://www.interserver.net/tips/kb/how-to-change-the-default-boot-target-on-linux-systems/

[^1_24]: https://docs.vllm.ai/en/latest/getting_started/quickstart/

[^1_25]: https://www.lions-wing.net/lessons/servers/home-server.html

[^1_26]: https://www.server-world.info/en/note?os=Ubuntu_24.04\&p=runlevel

[^1_27]: https://www.simplified.guide/docker/service-manage

[^1_28]: https://stackoverflow.com/questions/42438827/disable-docker-image-being-run-as-daemon-restart-always-policy

[^1_29]: https://amplifilabs.com/post/nomachine-with-xfce-desktop-on-headless-vps-complete-setup-guide

[^1_30]: https://calljames.co/blog/docker-do-not-start-containers-on-startup-318


---

# Ok, pero enfócate más en el problema que es que  cuando se instalan vLLM, ollama o llama.cpp, el sistema deja scripts de autolaunch que consumen bastantes recursos en la jetson, evitando que se puedan ejecutar otras instancias de modelos, lo cual es poco eficiente para cargas dinámicas, pues en algunas ocasiones necesito ejecutar vLLM, en otras llama.cpp, DE MANERA que necesito que la jetson al iniciarse, solo autolaunch los servicios indispensables, incluyendo la conexión por vía SSH, y servicios como por ejemplo NoMachine. Ya me las arreglo yo para crear scripts que lancen las herramientas que vaya necesitando según el pipeline a implementar, pero en definitiva necesito que con cada restart mi NVIDIA Jetson Orin AGX 64gb con jetson 7.2, corra limpia, sin servicios en segundo plano, ni congelados, ni  procesos fantasma para evitar problemas de OOD. Te dejo algo de contexto:

Entendido: el problema real no es “instalar modelos”, sino que **ciertas instalaciones dejan persistencias de arranque y demonios residentes** que consumen RAM/VRAM y compiten con otras cargas de inferencia en tu Jetson, justo cuando necesitas alternar entre vLLM, Ollama y `llama.cpp` según el pipeline. La arquitectura correcta es hacer que el Jetson arranque **solo con servicios indispensables** —principalmente SSH y NoMachine— y que todo lo demás quede estrictamente bajo arranque manual o bajo tus propios scripts.[^2_1][^2_2][^2_3]

## Problema a resolver

Ollama, por diseño, instala un servicio `systemd` que arranca `ollama serve` en cada boot y lo mantiene con `Restart=always`; eso es útil para un servidor siempre encendido, pero es precisamente lo contrario a un nodo de inferencia dinámica y de arranque limpio. En cambio, vLLM se describe como una herramienta que se instala con `pip` y se ejecuta con `vllm serve` o `uv run`, mientras que `llama.cpp` se usa típicamente como binario/servidor lanzado por el usuario, no como servicio persistente por defecto. Por eso, el riesgo no es homogéneo: el mayor foco de “residuos” y autoarranque viene de Ollama, pero también debes auditar wrappers, unit files y contenedores que hayas creado alrededor de vLLM o `llama.cpp`.[^2_2][^2_1]

## Estado objetivo

El estado ideal al reiniciar tu Jetson AGX Orin 64 GB con JetPack 7.2 es este: arranque en modo texto, SSH activo, NoMachine disponible para acceso remoto gráfico cuando lo necesites, y ningún daemon de LLM cargado en segundo plano. En ese esquema, el sistema arranca “**limpio**”, y luego tú levantas manualmente el motor que corresponda al pipeline del momento, evitando procesos fantasma y consumo innecesario de memoria.[^2_3][^2_4][^2_5]

## Guía de implementación

1. Cambia el target por defecto a modo texto:
```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

Ese ajuste evita el entorno gráfico completo en el arranque y reduce la carga base del sistema.[^2_4][^2_6]

2. Habilita SSH como servicio indispensable:
```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

SSH debe quedar siempre disponible para administración remota sin depender de GUI.[^2_7][^2_8]

3. Mantén NoMachine como el único acceso gráfico permanente.
En Jetson headless, la práctica correcta es usar display virtual/X11 compatible con acceso remoto, porque el acceso gráfico directo sin monitor puede fallar si dependes de una sesión de escritorio completa.[^2_8][^2_3]
4. Deshabilita Docker al arranque si no lo necesitas siempre:
```bash
sudo systemctl disable docker
```

Si sí lo usas, asegura que los contenedores no queden con políticas de reinicio automáticas como `always` o `unless-stopped`.[^2_5][^2_9][^2_10]

5. Elimina cualquier servicio residual de Ollama:
```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Esto apunta justo al comportamiento documentado por Ollama para crear y habilitar su servicio de arranque.[^2_1]

6. Verifica que no existan otros servicios residuales:
```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama)'
```

Aquí debes revisar tanto servicios del sistema como de usuario, porque algunos wrappers de `llama.cpp` o scripts propios pueden vivir en `~/.config/systemd/user/`.[^2_2][^2_1]

## Limpieza postinstalación

Cada vez que instales una herramienta de inferencia, asume que puede dejar rastros. En Ollama eso es explícito: la documentación muestra el archivo `/etc/systemd/system/ollama.service` y su activación automática, así que después de instalar debes auditar y eliminar cualquier autoarranque no deseado antes de usar el sistema en producción. Para vLLM y `llama.cpp`, el control debe estar en tus propios scripts de inicio, no en un servicio global oculto; su modelo natural de uso es ejecución explícita por comando, no persistencia automática.[^2_1][^2_2]

## Regla operativa

Tu política debe ser: “el sistema arranca vacío, y solo se levantan SSH y NoMachine; todo motor de inferencia se inicia manualmente o por scripts míos, y se mata al terminar”. Esa regla encaja muy bien con cargas dinámicas, porque evita que una instancia olvidada de Ollama o un contenedor con reinicio automático te bloquee memoria para otra corrida de vLLM o `llama.cpp`.[^2_9][^2_5][^2_1]

## Comandos base recomendados

```bash
sudo systemctl set-default multi-user.target
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo systemctl disable docker
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Si quieres, el siguiente paso es que te lo convierta en una **guía formal de hardening** con formato profesional: introducción del problema, objetivos, prerequisitos, procedimiento, verificación y checklist final para tu Jetson.
<span style="display:none">[^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_20][^2_21][^2_22][^2_23][^2_24]</span>

<div align="center">⁂</div>

[^2_1]: https://docs.ollama.com/linux

[^2_2]: https://docs.vllm.ai/en/v0.5.0/getting_started/installation.html

[^2_3]: https://www.stereolabs.com/docs/development/zed-sdk/virtual-display

[^2_4]: http://somebooks.es/iniciar-ubuntu-24-04-lts-sin-interfaz-grafica-parte-ii/

[^2_5]: https://stackoverflow.com/questions/37599128/docker-how-do-you-disable-auto-restart-on-a-container

[^2_6]: https://docs.redhat.com/es/documentation/red_hat_enterprise_linux/8/html/configuring_basic_system_settings/changing-the-default-target_working-with-systemd-targets

[^2_7]: https://forums.developer.nvidia.com/t/headless-mode-on-nvidia-jetson-agx-orin-64gb-with-jetpack-7-2/374718

[^2_8]: https://forums.developer.nvidia.com/t/problem-while-attempting-use-gui-in-headless-mode/167307

[^2_9]: https://oneuptime.com/blog/post/2026-01-16-docker-restart-policies/view

[^2_10]: https://github.com/moby/moby/issues/10032

[^2_11]: https://gitcode.csdn.net/69c2b17f0a2f6a37c59a0b22.html

[^2_12]: https://docs.ultralytics.com/fr/guides/nvidia-jetson

[^2_13]: https://www.youtube.com/watch?v=bTJy7ZluQto

[^2_14]: https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/SO/JetsonAgxOrin.html

[^2_15]: https://www.youtube.com/watch?v=TJC_xUUQKXM

[^2_16]: https://docs.ultralytics.com/es/guides/nvidia-jetson

[^2_17]: https://github.com/dusty-nv/jetson-containers/issues/805

[^2_18]: https://docs.viam.com/operate/reference/prepare/jetson-agx-orin-setup/

[^2_19]: https://github.com/ollama/ollama/issues/690

[^2_20]: https://noticias.mechatronicstore.cl/ia/maximizing-memory-efficiency-to-run-bigger-models-on-nvidia-jetson-d674facf95f5

[^2_21]: https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/quick_start.html

[^2_22]: https://forums.developer.nvidia.com/t/introducing-ollama-support-for-jetson-devices/289333

[^2_23]: https://forums.developer.nvidia.com/t/factory-reset-for-jetson-agx-orin/256422

[^2_24]: https://www.jetson-ai-lab.com/tutorials/ollama/


---

# Ok, te estás acercando, pero mira este hilo de gemini, aquí explico mucho más a detalle el problema:

"""
[https://share.gemini.google/v9l6bZGee1OF](https://share.gemini.google/v9l6bZGee1OF)
"""

Perfecto: ese contexto refuerza mucho mejor el diagnóstico. El problema no es solo “evitar que arranque la GUI”, sino **controlar la persistencia que dejan vLLM, Ollama y `llama.cpp` después de instalarse o ejecutarse mediante wrappers**, porque eso puede consumir RAM, GPU y procesos de fondo justo cuando necesitas alternar entre distintos motores de inferencia en el mismo Jetson.[^3_1][^3_2][^3_3]

## Problema central

En tu Jetson Orin AGX 64 GB, el costo de tener un servicio “siempre arriba” es alto: un daemon residente puede quedarse cargado, reservar memoria y provocar fallos de carga, timeouts o errores de asignación al intentar levantar otra instancia de modelo. En Ollama esto se ve con claridad, porque su instalación y su servicio `ollama.service` están pensados para disponibilidad continua, no para una estación de inferencia dinámica que debe arrancar vacía. Ese patrón choca con tu flujo de trabajo, donde un día necesitas vLLM, otro día `llama.cpp`, y no quieres que quede ningún proceso fantasma interponiéndose entre reinicios.[^3_2][^3_3][^3_8][^3_9][^3_11][^3_1]

## Qué debe pasar al arrancar

Tu sistema debería iniciar únicamente con lo indispensable: red, SSH y NoMachine. Todo lo relacionado con inferencia debe quedar desactivado por defecto y arrancarse solo cuando tú lo ordenes desde un script o sesión explícita, porque vLLM se usa como servidor/CLI lanzado manualmente y `llama.cpp` también se consume típicamente como binario o servicio creado por el usuario, no como residente obligatorio del sistema. Así conviertes la Jetson en un nodo de ejecución controlado, no en una máquina que “adivina” qué modelo quiere estar vivo después del reboot.[^3_3][^3_11][^3_12][^3_13][^3_14]

## Enfoque correcto

La estrategia correcta es tratar cada instalación como una posible fuente de persistencia y auditarla después de cada cambio. Ollama es el principal caso a neutralizar porque su documentación y reportes muestran que instala servicio propio y puede usar reinicio automático; vLLM, por su parte, normalmente entra por `pip` y no crea autoarranque por defecto, mientras que `llama.cpp` suele depender de wrappers o unit files que tú mismo o terceros puedan haber agregado. Por eso, el “arranque limpio” no se logra solo desinstalando software, sino **eliminando unidades de `systemd`, servicios de usuario y políticas de reinicio de Docker** que queden atrás.[^3_8][^3_11][^3_12][^3_15][^3_16][^3_17]

## Política de arranque limpia

1. El sistema debe arrancar en `multi-user.target`, no en escritorio completo.[^3_18][^3_19]
2. SSH debe estar habilitado permanentemente.[^3_14][^3_20]
3. NoMachine debe ser el único acceso gráfico persistente, idealmente con display virtual compatible con headless.[^3_13][^3_20]
4. Docker no debe arrancar solo si no es necesario, y los contenedores de LLM deben quedar con `--restart=no`.[^3_15][^3_16]
5. Ollama debe quedar sin `ollama.service` activo ni habilitado tras cada instalación o prueba.[^3_11][^3_1]
6. Cualquier wrapper de `llama.cpp` o script de vLLM debe vivir solo bajo tu control, no como servicio silencioso del sistema.[^3_12][^3_8]

## Redacción más precisa del objetivo

Podrías formular el objetivo así:

> “Necesito que mi NVIDIA Jetson Orin AGX 64 GB con JetPack 7.2 arranque siempre en un estado mínimo y predecible, sin servicios de inferencia residuales ni procesos en segundo plano asociados a vLLM, Ollama o `llama.cpp`. Solo deben levantarse los servicios indispensables para administración remota, como SSH y NoMachine, mientras que cualquier motor de inferencia se iniciará manualmente según el pipeline que vaya a ejecutar.”

Esa formulación deja claro que el foco no es el software en sí, sino **el control del estado del sistema entre reinicios**.[^3_11][^3_12][^3_13]

## Implicación práctica

Esto significa que, tras instalar cualquier motor, tu rutina debe incluir una verificación de persistencia: revisar `systemd`, revisar servicios de usuario, revisar contenedores y revisar scripts de shell que puedan estar lanzando procesos al iniciar sesión. En Ollama, el riesgo es evidente por su servicio dedicado; en vLLM y `llama.cpp`, el riesgo suele venir de la integración que tú o un wrapper hayan añadido encima. Esa disciplina es la que realmente evita la “memoria ocupada” y los bloqueos al arrancar otra inferencia distinta.[^3_1][^3_3][^3_8][^3_12][^3_11]

Si quieres, el siguiente paso es que te reescriba todo esto como una **especificación técnica formal**, empezando por el problema, luego los objetivos, la arquitectura deseada y finalmente el procedimiento de hardening.
<span style="display:none">[^3_10][^3_4][^3_5][^3_6][^3_7]</span>

<div align="center">⁂</div>

[^3_1]: https://github.com/ollama/ollama/issues/7161

[^3_2]: https://forums.developer.nvidia.com/t/ollama-timing-out-when-attempting-to-use-gpu-instead-of-cpu/301477

[^3_3]: https://github.com/ollama/ollama/issues/4256

[^3_4]: https://forums.developer.nvidia.com/t/ollama-and-jetson-issue/278708

[^3_5]: https://forums.developer.nvidia.com/t/issue-with-nvidia-jetson-agx-orin-developer-kit-64-gb/337837

[^3_6]: https://forums.developer.nvidia.com/t/how-to-run-vllm-0-11-0-on-jetson-agx-orin/353177

[^3_7]: https://github.com/AlexsJones/llmfit/issues/295

[^3_8]: https://github.com/vllm-project/vllm/issues/5640

[^3_9]: https://github.com/dusty-nv/jetson-containers/issues/814

[^3_10]: https://forums.developer.nvidia.com/t/ollama-errors-orin-nano/345290

[^3_11]: https://docs.ollama.com/linux

[^3_12]: https://docs.vllm.ai/en/v0.5.0/getting_started/installation.html

[^3_13]: https://www.stereolabs.com/docs/development/zed-sdk/virtual-display

[^3_14]: https://forums.developer.nvidia.com/t/headless-mode-on-nvidia-jetson-agx-orin-64gb-with-jetpack-7-2/374718

[^3_15]: https://oneuptime.com/blog/post/2026-01-16-docker-restart-policies/view

[^3_16]: https://stackoverflow.com/questions/37599128/docker-how-do-you-disable-auto-restart-on-a-container

[^3_17]: https://github.com/moby/moby/issues/10032

[^3_18]: http://somebooks.es/iniciar-ubuntu-24-04-lts-sin-interfaz-grafica-parte-ii/

[^3_19]: https://docs.redhat.com/es/documentation/red_hat_enterprise_linux/8/html/configuring_basic_system_settings/changing-the-default-target_working-with-systemd-targets

[^3_20]: https://forums.developer.nvidia.com/t/problem-while-attempting-use-gui-in-headless-mode/167307


---

# Especificación técnica formal

## 1. Problema

La NVIDIA Jetson Orin AGX 64 GB con JetPack 7.2 se usa para ejecutar cargas de inferencia local de manera dinámica, alternando entre vLLM, Ollama y `llama.cpp` según el pipeline requerido. El problema es que algunas instalaciones y wrappers dejan artefactos de arranque automático, servicios residentes o políticas de reinicio que consumen memoria y mantienen procesos activos incluso después del reboot.

Ese comportamiento es incompatible con un entorno de inferencia eficiente, porque la Jetson debe arrancar con la mayor cantidad posible de recursos libres para evitar contención de RAM, procesos fantasma y fallos de carga al iniciar otro modelo. En particular, Ollama es el caso más sensible porque su instalación puede registrar un servicio propio de `systemd` para ejecución continua.

## 2. Objetivos

### 2.1 Objetivo general

Definir una arquitectura de arranque mínimo y controlado para que la Jetson inicie siempre en un estado limpio, sin servicios de inferencia persistentes y con solo los servicios indispensables activos.

### 2.2 Objetivos específicos

- Evitar el autoarranque de servicios asociados a vLLM, Ollama y `llama.cpp`.
- Mantener activos solo los servicios esenciales para administración remota.
- Garantizar acceso remoto por SSH.
- Mantener NoMachine disponible para acceso gráfico remoto cuando sea necesario.
- Eliminar políticas de reinicio automático en contenedores y servicios no esenciales.
- Establecer un procedimiento repetible de hardening y verificación después de cada instalación o cambio.


## 3. Arquitectura deseada

### 3.1 Estado de arranque

El sistema debe iniciar en modo texto, sin entorno gráfico local por defecto. La configuración base debe usar `multi-user.target` como objetivo de arranque, de forma que no se cargue la pila completa de escritorio durante el boot.

### 3.2 Servicios indispensables

Los únicos servicios que deben permanecer habilitados por defecto son:

- SSH, para administración remota.
- NoMachine, para acceso gráfico remoto controlado.
- Servicios de red estrictamente necesarios para conectividad.


### 3.3 Servicios no deseados

Deben permanecer deshabilitados, no habilitados o totalmente eliminados:

- `ollama.service` u otros servicios creados por el instalador de Ollama.
- Unidades de `systemd` personalizadas para vLLM o `llama.cpp` que no sean necesarias.
- Contenedores Docker con políticas `always` o `unless-stopped`.
- Demonio Docker, salvo que se active manualmente por necesidad operativa.


### 3.4 Principio operativo

La Jetson no debe “decidir” qué motor de inferencia ejecutar al arrancar. La lógica debe ser inversa: el sistema arranca vacío y el usuario activa explícitamente el motor requerido mediante scripts o comandos controlados.

## 4. Procedimiento de hardening

### 4.1 Preparación inicial

Partir de una instalación limpia de JetPack 7.2. Si el sistema ya tuvo usos previos, se recomienda una reinstalación limpia para eliminar residuos de servicios, archivos de usuario y configuraciones heredadas.

### 4.2 Cambio de objetivo de arranque

Configurar el sistema para que arranque en modo texto:

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```


### 4.3 Habilitación de acceso remoto

Instalar y habilitar SSH:

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

Configurar una IP estática para mantener la conectividad consistente tras cada reinicio.

### 4.4 Configuración de NoMachine

Instalar NoMachine únicamente como solución de acceso gráfico remoto. Si se requiere modo headless, debe operar sobre una pantalla virtual o una configuración compatible con X11, sin depender de una sesión gráfica local completa.

### 4.5 Desactivación de persistencias de LLM

Auditar y limpiar cualquier rastro de servicios de inferencia:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama)'
```

Si existe `ollama.service`, debe ser detenido, deshabilitado y eliminado:

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Si existen servicios de usuario o wrappers creados para `llama.cpp` o vLLM, deben deshabilitarse desde su ubicación correspondiente.

### 4.6 Control de Docker

Si Docker no es imprescindible al arranque, debe permanecer deshabilitado:

```bash
sudo systemctl disable docker
```

Si existen contenedores ya creados, se debe neutralizar su reinicio automático:

```bash
docker update --restart=no $(docker ps -a -q)
```


### 4.7 Limpieza de residuos de usuario

Revisar rutas como:

- `~/.config/systemd/user/`
- `~/.bashrc`
- `~/.profile`

El objetivo es eliminar cualquier script que inicie procesos de forma silenciosa al entrar en sesión.

## 5. Criterios de verificación

La implementación se considera correcta si, después de reiniciar:

- El sistema arranca en `multi-user.target`.
- SSH está activo.
- NoMachine está disponible solo como acceso remoto controlado.
- No hay servicios de Ollama, vLLM o `llama.cpp` habilitados automáticamente.
- Docker no levanta contenedores por sí solo.
- No existen procesos de inferencia residuales consumiendo memoria al inicio.


## 6. Regla de operación

Toda carga de inferencia debe ejecutarse bajo demanda. Ningún motor debe quedar residente por defecto tras un reboot. El sistema debe funcionar como base limpia de ejecución, no como servidor persistente de inferencia.

## 7. Resultado esperado

Con esta arquitectura, la Jetson arranca con recursos libres, sin contaminación de servicios previos y sin procesos fantasma. Eso permite alternar entre vLLM, Ollama y `llama.cpp` según el pipeline, sin comprometer memoria ni estabilidad del sistema.

Si lo deseas, en el siguiente paso puedo convertir esta especificación en un **documento técnico estilo RFC o SOP**, con numeración formal, lenguaje normativo y anexos de comandos.

---

# Ok, perfecto, pero añade como 8 un apartado que especifique que; como esos servicios y pipelines van a ser utilizados o lanzados a voluntad del usuario. Se deben cambiar los comportamientos de autolaunch, por scripts con su respectivo "alias" en el .bashrc para facilitar el lanzamiento de estos servicios, junto con sus librerías y todo lo necesario para que corran sin problema. De modo que, lo que se busca es dinamizar el uso de la jetson, para en un momento utilizar vLLM, en otro llama.cpp, en otro Ollama, o incluso usar las 3 en simultánea para pipelines complejos, pero este comportamiento debe ser dirigido, pues se requiere que la jetson inicie cada ejecución en limpio, sin contenedores, sin LLM cargados, nada, totalmente limpio, solo los servicios indispensables para SSH y las librerías y procesos previamente instalados y configurados para correr NoMachine, en caso de requerir acceso a la jetson por entorno gráfico.

Sí, ese apartado encaja perfecto y fortalece la especificación. Debe dejar explícito que el arranque limpio no significa “prohibir” vLLM, Ollama o `llama.cpp`, sino **sacar su activación del boot y moverla a scripts de usuario con aliases controlados**, para que la Jetson se use como plataforma dinámica y no como servidor residente permanente.[^5_1][^5_2][^5_3]

## 8. Lanzamiento bajo demanda

Los motores de inferencia y sus pipelines asociados deben ejecutarse únicamente por decisión explícita del usuario. En lugar de autolaunch al inicio del sistema, cada herramienta debe disponerse mediante scripts propios de arranque, idealmente ubicados en un directorio de trabajo del usuario y expuestos mediante `alias` o funciones en `.bashrc` para facilitar su invocación manual.[^5_2][^5_3][^5_1]

El objetivo operativo es que la Jetson arranque siempre en estado limpio, sin contenedores activos, sin LLM cargados y sin demonios de inferencia persistentes; después, el usuario elige si necesita levantar vLLM, `llama.cpp`, Ollama o una combinación de los tres para pipelines más complejos. Esto es coherente con el uso típico de estas herramientas como comandos, servidores o wrappers lanzados por el usuario, no como cargas que deban permanecer residentes tras cada reinicio.[^5_4][^5_5][^5_1]

### 8.1 Principio de ejecución

Cada herramienta debe tener su propio script de lanzamiento con parámetros, variables de entorno, carga de bibliotecas y validaciones previas. El usuario invocará ese script a través de un alias en `.bashrc`, de modo que la experiencia sea rápida pero el comportamiento siga siendo totalmente explícito y controlado.[^5_3][^5_1][^5_2]

### 8.2 Ejemplo de política operativa

- `alias vllm_start=...`
- `alias llama_start=...`
- `alias ollama_start=...`

Cada alias debe apuntar a un script que levante el entorno correspondiente, y no a un servicio habilitado en boot. Esa separación permite alternar entre motores según el pipeline del momento, o incluso correr varios en paralelo cuando la memoria y el caso de uso lo permitan, sin perder el principio de arranque limpio.[^5_6][^5_5][^5_1]

### 8.3 Requisito de limpieza al reinicio

Al reiniciar, no debe quedar ningún modelo residente, ningún contenedor automático y ningún proceso de LLM persistente. Solo deben permanecer activos SSH y, si se requiere interfaz remota, los componentes necesarios para NoMachine. Todo lo demás debe reactivarse manualmente mediante scripts del usuario cuando haga falta.[^5_7][^5_8][^5_9]

## Texto consolidado del apartado 8

Si quieres dejarlo listo para insertarlo en tu especificación, puedes usar este texto:

> **8. Lanzamiento bajo demanda de motores de inferencia.**
> Los servicios, motores y pipelines de inferencia local deben ejecutarse únicamente a voluntad del usuario. Para ello, se prohíbe el autolaunch en el arranque del sistema y se reemplaza por scripts de inicio mantenidos por el usuario, expuestos mediante alias en `.bashrc` u otro mecanismo equivalente de shell. Cada script deberá cargar sus dependencias, variables de entorno, rutas de modelos y parámetros de ejecución necesarios para vLLM, Ollama, `llama.cpp` o combinaciones entre ellos. El sistema debe iniciar siempre en estado limpio, sin contenedores activos, sin LLM cargados y sin procesos persistentes de inferencia, reservando únicamente los servicios indispensables de conectividad remota, como SSH, y los componentes necesarios para NoMachine cuando se requiera acceso gráfico remoto.[^5_5][^5_8][^5_1][^5_3]

Puedo ahora integrarte todo el documento completo, ya con este punto 8 incluido y con redacción uniforme de especificación técnica formal.
<span style="display:none">[^5_10][^5_11][^5_12][^5_13][^5_14]</span>

<div align="center">⁂</div>

[^5_1]: https://github.com/royborgen/llama

[^5_2]: https://www.linkedin.com/posts/omarebnelkhattab-hosney-9a931b3_for-lunix-or-macos-user-a-tip-for-integrating-activity-7200644690881241088-DD1J

[^5_3]: https://github.com/xcvrys/ollama-bash-starter

[^5_4]: https://news.ycombinator.com/item?id=42274489

[^5_5]: https://docs.vllm.ai/en/v0.5.0/getting_started/installation.html

[^5_6]: https://nuxnik.com/install-and-use-ollama-on-your-local-machine/

[^5_7]: https://docs.ollama.com/linux

[^5_8]: https://www.stereolabs.com/docs/development/zed-sdk/virtual-display

[^5_9]: https://oneuptime.com/blog/post/2026-01-16-docker-restart-policies/view

[^5_10]: https://www.reddit.com/r/commandline/comments/1gsp34q/linux_command_line_aliases_for_local_llms_with/

[^5_11]: https://github.com/dusty-nv/jetson-containers/issues/805

[^5_12]: https://gitcode.csdn.net/69c2b17f0a2f6a37c59a0b22.html

[^5_13]: https://docs.ollama.com/faq

[^5_14]: https://gist.github.com/sohang3112/0772cb7676bda008aaf5430a10f7b893


---

# Especificación técnica formal

## 1. Problema

La NVIDIA Jetson Orin AGX 64 GB con JetPack 7.2 se utilizará como plataforma de inferencia local dinámica para alternar entre vLLM, Ollama y `llama.cpp` según el pipeline requerido. El problema principal es que estas herramientas y sus wrappers pueden dejar servicios de arranque automático, demonios residentes, políticas de reinicio y scripts de sesión que consumen memoria y mantienen procesos activos incluso después del reinicio.[^6_1][^6_2][^6_3]

Ese comportamiento es ineficiente para cargas dinámicas porque reduce la memoria disponible, introduce procesos fantasma y puede interferir con la ejecución de otra instancia de modelo o con otra herramienta de inferencia que el usuario quiera lanzar posteriormente. En Ollama, además, su documentación oficial incluye explícitamente la creación de un servicio `ollama.service` con `Restart=always`, lo cual confirma que su instalación puede orientar el sistema hacia disponibilidad continua y no hacia arranque limpio.[^6_2][^6_4][^6_5][^6_6]

## 2. Objetivos

### 2.1 Objetivo general

Definir una arquitectura de arranque mínimo y controlado para que la Jetson inicie siempre en un estado limpio, sin LLM cargados, sin contenedores activos y sin servicios de inferencia persistentes, manteniendo solo los servicios indispensables.

### 2.2 Objetivos específicos

- Evitar el autoarranque de servicios asociados a vLLM, Ollama y `llama.cpp`.
- Mantener activos solo SSH y los componentes necesarios para NoMachine.
- Asegurar que el sistema arranque en un target no gráfico por defecto.
- Eliminar políticas de reinicio automático en contenedores y unidades no esenciales.
- Reemplazar el autolaunch por scripts y aliases controlados por el usuario.
- Permitir que el usuario active de forma explícita vLLM, Ollama, `llama.cpp` o combinaciones entre ellos.


## 3. Arquitectura deseada

### 3.1 Estado de arranque

El sistema debe iniciar en `multi-user.target`, es decir, en modo texto y sin entorno gráfico local por defecto. Esto reduce la carga base del sistema y evita el arranque innecesario de la pila de escritorio.[^6_7][^6_8]

### 3.2 Servicios indispensables

Los únicos servicios que deben permanecer habilitados por defecto son:

- SSH, para administración remota.
- NoMachine, para acceso gráfico remoto cuando sea necesario.
- Servicios estrictamente necesarios de red y sistema.


### 3.3 Servicios no deseados

Deben permanecer deshabilitados o eliminados:

- `ollama.service` y cualquier override que lo reactive.[^6_2]
- Unidades personalizadas de `systemd` creadas para vLLM o `llama.cpp` si no son indispensables.
- Contenedores Docker con reinicio automático.
- Cualquier script de inicio de sesión que lance procesos de inferencia sin orden explícita.


### 3.4 Principio operativo

La Jetson no debe iniciar ningún motor de inferencia por sí sola. La activación de vLLM, Ollama o `llama.cpp` debe ocurrir solo mediante comandos o scripts del usuario, nunca por arranque del sistema.[^6_3][^6_1]

## 4. Procedimiento de hardening

### 4.1 Preparación inicial

Se recomienda partir de una instalación limpia de JetPack 7.2. Si el dispositivo tuvo configuraciones anteriores, debe hacerse una depuración completa para evitar residuos de servicios, archivos de usuario o unidades persistentes.

### 4.2 Cambio de objetivo de arranque

Configurar el sistema para arrancar en modo texto:

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

Ese ajuste evita el entorno gráfico completo al iniciar y hace que el sistema arranque en un estado mucho más liviano.[^6_8][^6_7]

### 4.3 Habilitación de acceso remoto

Instalar y habilitar SSH:

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

SSH debe ser el canal principal de administración remota. Si se requiere GUI remota, NoMachine debe quedar preparado como servicio o componente disponible, pero no como entorno local permanente.[^6_9][^6_10]

### 4.4 Configuración de NoMachine

NoMachine debe operar como acceso gráfico remoto bajo demanda. En escenarios headless, conviene una configuración compatible con X11 o pantalla virtual, para evitar dependencia de una sesión gráfica local completa.[^6_10][^6_9]

### 4.5 Desactivación de persistencias de LLM

Auditar servicios del sistema y del usuario:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama)'
```

Si existe `ollama.service`, debe ser detenido, deshabilitado y eliminado:

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Esto es especialmente importante porque Ollama documenta explícitamente la instalación de su servicio de arranque y su configuración con `Restart=always`.[^6_2]

### 4.6 Control de Docker

Si Docker no debe quedar activo permanentemente, deshabilítalo:

```bash
sudo systemctl disable docker
```

Si hay contenedores ya creados, neutraliza su política de reinicio:

```bash
docker update --restart=no $(docker ps -a -q)
```

Con ello se evita que contenedores olvidados o configurados como `always` consuman recursos al reiniciar Docker o el sistema.[^6_11][^6_12]

### 4.7 Limpieza de residuos de usuario

Revisar rutas de sesión y arranque del usuario:

- `~/.config/systemd/user/`
- `~/.bashrc`
- `~/.profile`

La meta es eliminar cualquier script o unidad que lance procesos de inferencia al iniciar sesión.

## 5. Criterios de verificación

La implementación se considera correcta si, después de reiniciar:

- El sistema arranca en `multi-user.target`.
- SSH está activo.
- NoMachine está disponible para acceso remoto cuando se requiera.
- No existen servicios de Ollama, vLLM o `llama.cpp` habilitados automáticamente.
- Docker no levanta contenedores por sí solo.
- No hay procesos de inferencia residuales consumiendo memoria al inicio.


## 6. Regla de operación

Toda carga de inferencia debe ejecutarse bajo demanda. Ningún motor debe quedar residente por defecto tras un reboot. El sistema debe comportarse como base limpia de ejecución, no como servidor persistente de LLM.

## 7. Resultado esperado

Con esta arquitectura, la Jetson arranca con la mayor cantidad posible de recursos libres y sin contaminación de servicios anteriores. Esto permite alternar entre vLLM, Ollama y `llama.cpp` sin comprometer memoria ni estabilidad del sistema.[^6_4][^6_5][^6_6]

## 8. Lanzamiento bajo demanda de motores de inferencia

Los servicios, motores y pipelines de inferencia local deben ejecutarse únicamente a voluntad del usuario. Se prohíbe el autolaunch en el arranque del sistema y se reemplaza por scripts de inicio mantenidos por el usuario, expuestos mediante `alias` en `.bashrc` u otro mecanismo equivalente de shell.[^6_13][^6_14][^6_15]

Cada script debe encargarse de cargar dependencias, variables de entorno, rutas de modelos, bibliotecas y parámetros de ejecución necesarios para vLLM, Ollama, `llama.cpp` o combinaciones entre ellos. El sistema debe iniciar siempre en estado limpio, sin LLM cargados, sin contenedores activos y sin procesos persistentes de inferencia, reservando únicamente los servicios indispensables de conectividad remota, como SSH, y los componentes necesarios para NoMachine cuando se requiera acceso gráfico remoto.[^6_9][^6_13][^6_2]

### 8.1 Principio de ejecución

Cada herramienta debe contar con su propio script de arranque. El usuario invocará ese script a través de un alias o función en `.bashrc`, de manera que el lanzamiento sea rápido pero siga siendo explícito y controlado.[^6_14][^6_15][^6_13]

### 8.2 Política de alias

Se recomienda usar alias o funciones como:

- `alias vllm_start=...`
- `alias llama_start=...`
- `alias ollama_start=...`

Cada alias debe apuntar a un script que levante el entorno correspondiente y no a un servicio habilitado en boot. Esa separación permite alternar entre motores según el pipeline, o incluso correr varios en simultánea si la carga y la memoria lo permiten.[^6_13][^6_14]

### 8.3 Requisito de limpieza al reinicio

Al reiniciar, no debe quedar ningún modelo residente, ningún contenedor automático y ningún proceso persistente de inferencia. Solo deben permanecer activos SSH y, si se requiere interfaz remota, los componentes necesarios para NoMachine. Todo lo demás debe reactivarse manualmente mediante scripts del usuario.[^6_16][^6_9][^6_2]

## 9. Anexo de implementación operativa

Ejemplo de base mínima de hardening:

```bash
sudo systemctl set-default multi-user.target
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo systemctl disable docker
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Luego, cada motor debe iniciarse desde un script propio del usuario, no desde el boot del sistema. Eso preserva la dinámica de uso que necesitas: un día vLLM, otro `llama.cpp`, otro Ollama, o una combinación de los tres para pipelines complejos, pero siempre con arranque limpio y control explícito.[^6_17][^6_1][^6_3]

Si quieres, puedo convertir esta especificación en una **versión final tipo documento técnico formal** con estilo más normativo, enumeración de requisitos y formato listo para pegar en un informe o README.
<span style="display:none">[^6_18][^6_19][^6_20][^6_21][^6_22]</span>

<div align="center">⁂</div>

[^6_1]: https://docs.vllm.ai/en/stable/getting_started/quickstart/

[^6_2]: https://docs.ollama.com/linux

[^6_3]: https://github.com/ollama/ollama/issues/5165

[^6_4]: https://github.com/ollama/ollama/issues/7161

[^6_5]: https://forums.developer.nvidia.com/t/ollama-timing-out-when-attempting-to-use-gpu-instead-of-cpu/301477

[^6_6]: https://github.com/ollama/ollama/issues/4256

[^6_7]: https://dev.to/vonusma/headless-mode-on-nvidia-jetson-agx-orin-64gb-with-jetpack-72-448a

[^6_8]: https://eteo.tistory.com/997

[^6_9]: https://www.stereolabs.com/docs/development/zed-sdk/virtual-display

[^6_10]: https://forums.developer.nvidia.com/t/problem-while-attempting-use-gui-in-headless-mode/167307

[^6_11]: https://stackoverflow.com/questions/37599128/docker-how-do-you-disable-auto-restart-on-a-container

[^6_12]: https://github.com/moby/moby/issues/10032

[^6_13]: https://github.com/royborgen/llama

[^6_14]: https://www.linkedin.com/posts/omarebnelkhattab-hosney-9a931b3_for-lunix-or-macos-user-a-tip-for-integrating-activity-7200644690881241088-DD1J

[^6_15]: https://github.com/xcvrys/ollama-bash-starter

[^6_16]: https://oneuptime.com/blog/post/2026-01-16-docker-restart-policies/view

[^6_17]: https://docs.vllm.ai/en/v0.5.0/getting_started/installation.html

[^6_18]: https://www.linuxmaster.jp/linux_skill/2026/06/ollama-systemd-service-autostart.html

[^6_19]: https://forums.developer.nvidia.com/t/headless-os/72232

[^6_20]: https://github.com/dusty-nv/jetson-containers/issues/805

[^6_21]: https://forums.developer.nvidia.com/t/headless-operation/177394

[^6_22]: https://github.com/ollama/ollama/issues/11517


---

# This is my local context:

"""
jetson@jetson-orin:~\$ systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
docker.service                               enabled         enabled
llama-server.service                         enabled         enabled
ollama.service                               disabled        enabled
vllm-container.service                       enabled         enabled
jetson@jetson-orin:~\$ systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama)'
jetson@jetson-orin:~\$ systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
docker.service                               enabled         enabled
llama-server.service                         enabled         enabled
ollama.service                               disabled        enabled
vllm-container.service                       enabled         enabled
jetson@jetson-orin:~\$ sudo systemctl stop ollama
[sudo] password for jetson:
jetson@jetson-orin:~\$ sudo systemctl disable ollama
jetson@jetson-orin:~\$ sudo rm -f /etc/systemd/system/ollama.service
jetson@jetson-orin:~\$ sudo systemctl daemon-reload
jetson@jetson-orin:~\$ sudo systemctl disable docker
Synchronizing state of docker.service with SysV service script with /usr/lib/systemd/systemd-sysv-install.
Executing: /usr/lib/systemd/systemd-sysv-install disable docker
Removed "/etc/systemd/system/multi-user.target.wants/docker.service".
Disabling 'docker.service', but its triggering units are still active:
docker.socket
jetson@jetson-orin:~\$ docker update --restart=no $(docker ps -a -q)
4a44e9ca8d8a
734cc7ce8f1c
fa6f4b43506e
27a58f28b8fa
f90ead354b36
jetson@jetson-orin:~$ cat ~/.config/systemd/user/
cat: /home/jetson/.config/systemd/user/: Is a directory
jetson@jetson-orin:~\$ ls -a ~/.config/systemd/user/
.  ..  default.target.wants  openclaw-gateway.service  openclaw-gateway.service.bak
jetson@jetson-orin:~\$ cat ~/.bashrc

# ~/.bashrc: executed by bash(1) for non-login shells.

# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)

# for examples

\#Hugging face and LLM keys
export HF_TOKEN="hf_oauth_e..."
export HUGGING_FACE_HUB_TOKEN="hf_oauth_e..."

\#NVIDIA Cuda JetPack
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

\#Rutas ejecutables locales y de usuario
export PATH="$PATH:/home/jetson/.local/bin"
export PATH="/home/jetson/.npm-global/bin:$PATH"

\#Jetson Containers
export PATH=$HOME/jetson-containers:$PATH

# OpenClaw y agentes

export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1

export VLLM_API_KEY="none"

# If not running interactively, don't do anything

case \$- in
*i*) ;;
*) return;;
esac

# don't put duplicate lines or lines starting with space in the history.

# See bash(1) for more options

HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it

shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)

HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,

# update the values of LINES and COLUMNS.

shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will

# match all files and zero or more directories and subdirectories.

\#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)

[ -x /usr/bin/lesspipe ] \&\& eval "\$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)

if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)

case "\$TERM" in
xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned

# off by default to not distract the user: the focus in a terminal window

# should be on the output of commands, not on the prompt

\#force_color_prompt=yes

if [ -n "\$force_color_prompt" ]; then
if [ -x /usr/bin/tput ] \&\& tput setaf 1 >\&/dev/null; then
\# We have color support; assume it's compliant with Ecma-48
\# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
\# a case would tend to support setf rather than setaf.)
color_prompt=yes
else
color_prompt=
fi
fi

if [ "\$color_prompt" = yes ]; then

    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
    else
PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir

case "\$TERM" in
xterm*|rxvt*)

    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
    *)
;;
esac

# enable color support of ls and also add handy aliases

if [ -x /usr/bin/dircolors ]; then
test -r ~/.dircolors \&\& eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
alias ls='ls --color=auto'
\#alias dir='dir --color=auto'
\#alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
    fi

# colored GCC warnings and errors

\#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:

# sleep 10; alert

alias alert='notify-send --urgency=low -i "\$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;\&|]\s*alert\$//'\'')"'

# Alias definitions.

# You may want to put all your additions into a separate file like

# ~/.bash_aliases, instead of adding them here directly.

# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
. ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable

# this, if it's already enabled in /etc/bash.bashrc and /etc/profile

# sources /etc/bash.bashrc).

if ! shopt -oq posix; then
if [ -f /usr/share/bash-completion/bash_completion ]; then
. /usr/share/bash-completion/bash_completion
elif [ -f /etc/bash_completion ]; then
. /etc/bash_completion
fi
fi

# Created by `pipx` on 2026-06-27 01:17:27

eval "\$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"

# OpenClaw Completion

[ -f "/home/jetson/.openclaw/completions/openclaw.bash" ] \&\& source "/home/jetson/.openclaw/completions/openclaw.bash"

export PATH="/opt/ngc-cli:$PATH"
alias jetson-clean='~/scripts/jetson-clean.sh'
jetson@jetson-orin:~$ cat ~/.profile

# ~/.profile: executed by the command interpreter for login shells.

# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login

# exists.

# see /usr/share/doc/bash/examples/startup-files for examples.

# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask

# for ssh logins, install and configure the libpam-umask package.

\#umask 022

# if running bash

if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
. "\$HOME/.bashrc"
fi
fi

# set PATH so it includes user's private bin if it exists

if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:\$PATH"
fi

# set PATH so it includes user's private bin if it exists

if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:\$PATH"
fi

# Created by `pipx` on 2026-06-27 01:17:27

export PATH="$PATH:/home/jetson/.local/bin"
export HF_TOKEN=hf_YOUR_TOKEN_HERE
jetson@jetson-orin:~$
"""

Perfecto: con ese contexto ya se ve con mucha claridad **qué está generando el arranque sucio** y qué falta por corregir.

## Diagnóstico

Lo más importante es esto:

- `docker.service` sigue **enabled** y además el sistema te avisó que `docker.socket` sigue activo, así que Docker aún puede despertar por socket activation aunque hayas deshabilitado el servicio principal.
- `llama-server.service` sigue **enabled**, por lo que ese sí está dejando persistencia real en el boot.
- `vllm-container.service` sigue **enabled**, así que también queda residente al iniciar.
- `ollama.service` ya quedó **disabled** y además eliminaste el unit file, así que ese punto ya está bien encaminado.
- En el directorio de servicios de usuario sí hay un `openclaw-gateway.service` habilitado vía `default.target.wants`, lo cual indica que tu sesión de usuario también está contribuyendo al arranque automático.[^7_1]


## Lo que debes corregir primero

La prioridad inmediata debería ser:

1. Deshabilitar `llama-server.service`.
2. Deshabilitar `vllm-container.service`.
3. Deshabilitar `docker.socket`, no solo `docker.service`.
4. Revisar si esos servicios tienen unit files en `/etc/systemd/system/` o en otra ruta persistente.
5. Revisar `openclaw-gateway.service` en el ámbito de usuario y decidir si debe quedar fuera del arranque o moverse a lanzamiento manual.[^7_1]

## Observaciones sobre tus scripts de shell

Tu `~/.bashrc` y `~/.profile` no muestran, en lo que pegaste, un autoarranque directo de Ollama, vLLM o `llama.cpp`, pero sí hay varias cosas que conviene separar del arranque normal:

- Tokens y variables sensibles.
- Rutas y exportaciones de entorno.
- Integraciones de OpenClaw.
- Alias utilitarios como `jetson-clean`.

Eso no es malo por sí mismo, pero para tu objetivo de “arranque limpio” conviene mover lo que sea específico de inferencia a un archivo dedicado, por ejemplo `~/.bash_aliases_llm` o `~/scripts/llm-env.sh`, y dejar `.bashrc` más liviano y declarativo.[^7_1]

## Ajuste recomendado para tu arquitectura

Tu arquitectura debería quedar así:

- **Boot del sistema:** solo lo mínimo.
- **Servicios permanentes:** SSH y NoMachine.
- **Docker:** apagado por defecto.
- **LLM:** nada habilitado en boot.
- **vLLM / Ollama / llama.cpp:** solo por scripts manuales.
- **OpenClaw o cualquier gateway:** también bajo demanda, salvo que realmente sea indispensable.[^7_1]

Eso cumple con tu idea central: la Jetson arranca limpia, y luego tú decides si hoy ejecutas vLLM, mañana `llama.cpp`, o una combinación de ambos para un pipeline complejo.

## Redacción que puedes agregar a la especificación

Te propongo insertar un apartado adicional, o reforzar el punto 8, con esta redacción:

> Los motores de inferencia, servicios auxiliares y gateways asociados deberán permanecer deshabilitados durante el arranque del sistema. Cualquier componente que requiera recursos de GPU, memoria unificada o conectividad interna deberá activarse únicamente por decisión explícita del usuario mediante scripts o alias de shell. El propósito es evitar persistencias residuales, sockets de activación, servicios de usuario habilitados y contenedores reiniciados automáticamente, preservando un estado inicial completamente limpio para cada reinicio.[^7_1]

## Siguiente acción concreta

El siguiente paso lógico es depurar en este orden:

- `docker.socket`
- `llama-server.service`
- `vllm-container.service`
- `openclaw-gateway.service`

y luego verificar de nuevo el estado con un listado de servicios del sistema y de usuario para confirmar que el arranque quedó realmente limpio.[^7_1]

Si quieres, en el siguiente mensaje te dejo un **plan exacto de limpieza y reorganización** para:

1. deshabilitar lo que sobra,
2. dejar solo SSH y NoMachine, y
3. proponer una estructura limpia de `~/scripts/` y aliases para lanzar vLLM, Ollama y `llama.cpp` bajo demanda.

<div align="center">⁂</div>

[^7_1]: https://zenn.dev/nooop/articles/785b7c511f991b?locale=en


---

## Plan de limpieza y reorganización

### 1. Objetivo

Dejar la Jetson en un estado de arranque limpio y predecible, con solo los servicios indispensables activos, y mover todo lo demás a un esquema de lanzamiento bajo demanda. Eso significa que el sistema debe iniciar solo con SSH, NoMachine y lo mínimo de red, sin motores LLM residentes ni contenedores que se levanten solos.

### 2. Inventario de lo que hoy está afectando el arranque

Con el contexto que compartiste, el sistema todavía tiene estos puntos a corregir:

- `docker.service` sigue habilitado.
- `docker.socket` sigue activo.
- `llama-server.service` sigue habilitado.
- `vllm-container.service` sigue habilitado.
- Existe `openclaw-gateway.service` en `~/.config/systemd/user/default.target.wants/`.

Ollama ya fue limpiado correctamente a nivel de unidad del sistema, así que ese frente ya quedó resuelto.

### 3. Limpieza inmediata

Haz esta limpieza en este orden:

1. Deshabilita `llama-server.service`.
2. Deshabilita `vllm-container.service`.
3. Deshabilita `docker.socket`.
4. Revisa si esos servicios tienen archivos `.service` en `/etc/systemd/system/` o en otra ruta persistente.
5. Decide si `openclaw-gateway.service` debe seguir como servicio de usuario o pasar a arranque manual.
6. Vuelve a recargar el gestor de servicios.
7. Reinicia y verifica que no queden procesos ni servicios residuales.

### 4. Estado objetivo tras la limpieza

Después del reinicio, el sistema debe quedar así:

- Arranque en `multi-user.target`.
- SSH activo.
- NoMachine listo para uso remoto gráfico cuando lo necesites.
- Docker deshabilitado por defecto.
- Ningún servicio de vLLM, Ollama o `llama.cpp` habilitado al boot.
- Ningún contenedor autoarrancando.
- Ningún servicio de usuario lanzando procesos de inferencia sin permiso explícito.


### 5. Reorganización recomendada

Conviene separar el entorno en cuatro capas:

- **Capa base del sistema:** red, SSH, NoMachine y utilidades mínimas.
- **Capa de inferencia:** scripts manuales para vLLM, Ollama y `llama.cpp`.
- **Capa de soporte:** bibliotecas, modelos, caches y variables de entorno.
- **Capa de orquestación personal:** aliases y wrappers en shell.

Así evitas que una instalación deje residuos en el boot y, al mismo tiempo, mantienes velocidad operativa para lanzar cada herramienta cuando la necesites.

### 6. Estructura sugerida de scripts

Crea un directorio dedicado, por ejemplo:

```bash
~/scripts/llm/
```

Y divide ahí los lanzadores:

- `start-vllm.sh`
- `start-llama.sh`
- `start-ollama.sh`
- `stop-llm.sh`
- `env-llm.sh`

Cada script debe cargar sus variables, preparar rutas, activar lo necesario y luego iniciar la herramienta correspondiente.

### 7. Organización de aliases

En lugar de lanzar los motores desde servicios automáticos, expón comandos cortos en `~/.bashrc` o, mejor aún, en `~/.bash_aliases`:

- `alias vllm-start='~/scripts/llm/start-vllm.sh'`
- `alias llama-start='~/scripts/llm/start-llama.sh'`
- `alias ollama-start='~/scripts/llm/start-ollama.sh'`
- `alias llm-stop='~/scripts/llm/stop-llm.sh'`

Eso te permite arrancar el motor adecuado sin perder control del estado del sistema.

### 8. Manejo de variables y dependencias

No dejes tokens, rutas o configuraciones de ejecución mezcladas con el arranque general. Lo ideal es:

- mover variables de LLM a `~/scripts/llm/env-llm.sh`;
- dejar `.bashrc` solo con alias y cargas ligeras;
- mantener el acceso de NoMachine separado de los motores LLM;
- evitar que `~/.profile` cargue nada que dispare procesos de inferencia.


### 9. Política operativa

La política final debe ser esta:

- El sistema arranca vacío.
- Solo SSH y NoMachine quedan preparados.
- No hay contenedores activos.
- No hay LLM cargados.
- Cada motor se lanza solo por decisión explícita del usuario.
- Si un pipeline requiere vLLM, `llama.cpp` u Ollama, se activa en ese momento y luego se apaga.


### 10. Secuencia de validación

Después de reorganizar, valida:

- que no existan servicios habilitados de `llama-server` ni `vllm-container`;
- que `docker.socket` esté deshabilitado;
- que no haya servicios de usuario arrancando OpenClaw o LLMs sin intención;
- que al reiniciar no queden procesos de inferencia residentes;
- que los alias funcionen y levanten cada motor solo cuando tú lo pidas.


### 11. Resultado esperado

Con esta reorganización, la Jetson queda como un nodo dinámico de inferencia: limpia al reiniciar, ligera al arrancar y flexible al trabajar. Eso te permite usar vLLM, Ollama o `llama.cpp` de forma alternada o combinada, pero siempre bajo control explícito, sin contaminar el boot y sin perder memoria en procesos innecesarios.

Si quieres, en el siguiente mensaje te redacto esto mismo como un **procedimiento operativo paso a paso con comandos concretos**, listo para ejecutar en tu Jetson.
<span style="display:none">[^8_1][^8_10][^8_2][^8_3][^8_4][^8_5][^8_6][^8_7][^8_8][^8_9]</span>

<div align="center">⁂</div>

[^8_1]: https://www.youtube.com/watch?v=mNCCdnuldE0

[^8_2]: https://www.climprofesional.com/blog/limpieza-del-hogar-planificacion/

[^8_3]: https://es.scribd.com/document/690182257/GUIA-Casa-organizada-en-un-mes

[^8_4]: https://www.youtube.com/watch?v=98cQBXquCm0\&vl=es-ES

[^8_5]: https://es.scribd.com/document/368521162/Tabero-Pepa-Manual-De-La-Casa-Limpia-Y-Ordenada-doc

[^8_6]: https://www.occident.com/blog/limpieza-desinfeccion-semanal/

[^8_7]: https://www.lavanguardia.com/vivo/como-hacer-diy/20220327/8155280/como-organizar-limpieza-casa-7-pasos-nbs.html

[^8_8]: https://marketb2b.mx/Portal/Blog/904/plan-de-limpieza-en-casa

[^8_9]: https://ordenyespacios.com/como-organizar-una-limpieza-en-profundidad/

[^8_10]: https://www.lavanguardia.com/vivo/como-hacer-diy/20220327/8155280/como-organizar-limpieza-casa-7-pasos-nbs.amp.html


---

# Sí, por favor redacta el procedimiento paso a paso con comandos

Sí. Te dejo un procedimiento **paso a paso, con comandos**, orientado a dejar la Jetson limpia al arrancar y mover vLLM, Ollama y `llama.cpp` a ejecución manual bajo demanda.

## 1. Verificar estado actual

Primero confirma qué está habilitado hoy:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama|openclaw)'
systemctl get-default
```

Debes identificar especialmente `docker.service`, `docker.socket`, `llama-server.service`, `vllm-container.service` y cualquier servicio de usuario como `openclaw-gateway.service`.

## 2. Cambiar el arranque a modo limpio

Configura el sistema para iniciar sin GUI:

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

Tras volver a entrar, verifica:

```bash
systemctl get-default
```

Debe responder `multi-user.target`.

## 3. Habilitar SSH como servicio base

Asegura acceso remoto por consola:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo systemctl status ssh --no-pager
```

Si usas IP fija, configura Netplan antes de seguir con el resto.

## 4. Desactivar Docker completamente al arranque

Primero deshabilita el servicio principal:

```bash
sudo systemctl disable docker
```

Luego desactiva también el socket, porque si no puede volver a despertar Docker por activación bajo demanda:

```bash
sudo systemctl disable docker.socket
sudo systemctl stop docker.socket
sudo systemctl stop docker
```

Comprueba el estado:

```bash
systemctl status docker --no-pager
systemctl status docker.socket --no-pager
```


## 5. Eliminar autoarranque de Ollama

Si todavía existe el servicio o una copia residual, límpialo así:

```bash
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
```

Luego valida que ya no aparezca:

```bash
systemctl list-unit-files --type=service | grep -E 'ollama'
```


## 6. Deshabilitar llaves de arranque de vLLM y llama.cpp

Si existen estas unidades:

```bash
sudo systemctl stop llama-server.service 2>/dev/null || true
sudo systemctl disable llama-server.service 2>/dev/null || true

sudo systemctl stop vllm-container.service 2>/dev/null || true
sudo systemctl disable vllm-container.service 2>/dev/null || true

sudo systemctl daemon-reload
```

Si sospechas que hay archivos de unidad persistentes, búscalos:

```bash
sudo find /etc/systemd/system /lib/systemd/system -name '*llama*' -o -name '*vllm*' -o -name '*ollama*'
```

Si encuentras un archivo que no quieres mantener, elimínalo o muévelo a respaldo.

## 7. Revisar servicios de usuario

En tu caso apareció `openclaw-gateway.service` en el entorno de usuario. Revisa eso así:

```bash
systemctl --user list-unit-files --type=service | grep -E '(openclaw|ollama|vllm|llama)'
ls -la ~/.config/systemd/user/
ls -la ~/.config/systemd/user/default.target.wants/
```

Si `openclaw-gateway.service` no debe arrancar solo, deshabilítalo:

```bash
systemctl --user disable openclaw-gateway.service
systemctl --user daemon-reload
```

Si quieres ser más agresivo, puedes quitar el symlink de `default.target.wants`:

```bash
rm -f ~/.config/systemd/user/default.target.wants/openclaw-gateway.service
systemctl --user daemon-reload
```


## 8. Limpiar el shell de autoarranques no deseados

Tu `~/.bashrc` no muestra autolaunch directo de LLMs, pero sí conviene separar responsabilidades.

Crea una carpeta para scripts:

```bash
mkdir -p ~/scripts/llm
mkdir -p ~/scripts/llm/env
```

Crea un archivo de entorno dedicado, por ejemplo:

```bash
nano ~/scripts/llm/env/llm-env.sh
```

Puedes poner allí solo lo necesario para inferencia, por ejemplo:

```bash
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export PATH="$PATH:$HOME/.local/bin"
export PATH="$HOME/.npm-global/bin:$PATH"
```

Luego hazlo ejecutable:

```bash
chmod +x ~/scripts/llm/env/llm-env.sh
```


## 9. Crear scripts de arranque manual

### 9.1 vLLM

Ejemplo de script:

```bash
nano ~/scripts/llm/start-vllm.sh
```

Contenido base:

```bash
#!/usr/bin/env bash
set -e
source "$HOME/scripts/llm/env/llm-env.sh"
cd "$HOME"
vllm serve
```

Dale permisos:

```bash
chmod +x ~/scripts/llm/start-vllm.sh
```


### 9.2 llama.cpp

```bash
nano ~/scripts/llm/start-llama.sh
```

Ejemplo:

```bash
#!/usr/bin/env bash
set -e
source "$HOME/scripts/llm/env/llm-env.sh"
cd "$HOME"
./llama-server
```

Ajusta la ruta real del binario según tu instalación:

```bash
chmod +x ~/scripts/llm/start-llama.sh
```


### 9.3 Ollama

```bash
nano ~/scripts/llm/start-ollama.sh
```

Ejemplo:

```bash
#!/usr/bin/env bash
set -e
source "$HOME/scripts/llm/env/llm-env.sh"
ollama serve
```

Permisos:

```bash
chmod +x ~/scripts/llm/start-ollama.sh
```


## 10. Crear un script de parada

```bash
nano ~/scripts/llm/stop-llm.sh
```

Ejemplo:

```bash
#!/usr/bin/env bash
set -e
pkill -f 'vllm|ollama|llama-server' || true
```

Permisos:

```bash
chmod +x ~/scripts/llm/stop-llm.sh
```


## 11. Crear aliases en el shell

Edita `~/.bashrc`:

```bash
nano ~/.bashrc
```

Al final agrega algo como esto:

```bash
alias vllm-start='~/scripts/llm/start-vllm.sh'
alias llama-start='~/scripts/llm/start-llama.sh'
alias ollama-start='~/scripts/llm/start-ollama.sh'
alias llm-stop='~/scripts/llm/stop-llm.sh'
alias jetson-clean='~/scripts/jetson-clean.sh'
```

Luego recarga la shell:

```bash
source ~/.bashrc
```


## 12. Separar lo que debe quedar cargado siempre

Deja en el arranque normal solo lo indispensable:

- SSH.
- NoMachine.
- Variables mínimas del sistema.
- Nada que lance modelos, contenedores o gateways de inferencia.

Todo lo demás debe vivir en scripts explícitos.

## 13. Validar que el sistema quedó limpio

Después de aplicar los cambios, reinicia:

```bash
sudo reboot
```

Al volver, verifica:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama|openclaw)'
ps aux | grep -E '(ollama|vllm|llama-server)' | grep -v grep
```

El resultado esperado es que no queden servicios habilitados ni procesos residentes de LLM.

## 14. Regla final de operación

Desde ese punto, tu flujo debe ser:

1. Arranca la Jetson.
2. Entra por SSH o NoMachine.
3. Ejecuta el alias correspondiente.
4. Cuando termines, para el proceso.
5. Reinicia y confirma que el sistema vuelve a estar limpio.

Si quieres, el siguiente paso es que te escriba los archivos exactos `start-vllm.sh`, `start-llama.sh`, `start-ollama.sh` y `stop-llm.sh` listos para copiar y pegar.

---

# Ok, pero espera, este es el output del comando con todas las implementaciones realizadas:

"""
jetson@jetson-orin:~\$ systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama|openclaw)'
ps aux | grep -E '(ollama|vllm|llama-server)' | grep -v grep
docker.service                               disabled        enabled
llama-server.service                         disabled        enabled
vllm-container.service                       disabled        enabled
openclaw-gateway.service                                              disabled  enabled
jetson@jetson-orin:~\$
"""
Revisemos esto, y luego generas start-vllm.sh, start-llama.sh, start-ollama.sh y stop-llm.sh listos para copiar y pegar.

Sí, revisémoslo: el output indica que ya lograste **deshabilitar** varias unidades, pero todavía no has eliminado todas las fuentes posibles de activación. En `systemd`, “disabled” significa que no se inicia automáticamente en boot, pero el unit file puede seguir existiendo; y en Docker, si `docker.socket` sigue activo, el daemon puede despertarse por socket activation aunque `docker.service` esté deshabilitado.[^10_1][^10_2]

## Interpretación del estado actual

Tu salida muestra:

- `docker.service` → `disabled` con `vendor preset: enabled`.
- `llama-server.service` → `disabled` con `vendor preset: enabled`.
- `vllm-container.service` → `disabled` con `vendor preset: enabled`.
- `openclaw-gateway.service` → `disabled` con `vendor preset: enabled`.

Eso es bueno: ya no deberían arrancar automáticamente al boot por `systemd`. Pero el siguiente paso es verificar si esos servicios siguen presentes como archivos de unidad, si existen overrides, y si `docker.socket` sigue habilitado o activo, porque eso sería una vía secundaria de arranque.[^10_3][^10_4][^10_2][^10_1]

## Qué falta confirmar

Antes de escribir los scripts, conviene ejecutar estas comprobaciones:

```bash
systemctl is-enabled docker.service
systemctl is-enabled docker.socket
systemctl is-enabled llama-server.service
systemctl is-enabled vllm-container.service
systemctl is-enabled openclaw-gateway.service
```

Y también:

```bash
systemctl status docker.socket --no-pager
systemctl --user status openclaw-gateway.service --no-pager
```

Si `docker.socket` aparece activo o habilitado, debes apagarlo; si `openclaw-gateway.service` está habilitado en el ámbito de usuario, debes decidir si lo dejas manual o lo sacas del arranque.[^10_4][^10_2]

## Procedimiento de ajuste final

Te recomiendo este orden:

```bash
sudo systemctl stop docker.socket 2>/dev/null || true
sudo systemctl disable docker.socket 2>/dev/null || true

sudo systemctl stop docker 2>/dev/null || true
sudo systemctl disable docker 2>/dev/null || true

systemctl --user stop openclaw-gateway.service 2>/dev/null || true
systemctl --user disable openclaw-gateway.service 2>/dev/null || true
systemctl --user daemon-reload
```

Luego vuelve a revisar:

```bash
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker|openclaw)'
systemctl --user list-unit-files --type=service | grep -E '(ollama|vllm|llama|openclaw)'
```


## Scripts listos para copiar y pegar

A continuación te dejo los cuatro scripts como pediste.

## `~/scripts/llm/start-vllm.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

source "$HOME/scripts/llm/env/llm-env.sh"

export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HOME/.cache/huggingface/transformers}"
export VLLM_USE_V1=1

exec vllm serve "$@"
```


## `~/scripts/llm/start-llama.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

source "$HOME/scripts/llm/env/llm-env.sh"

LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin/llama-server}"

if [ ! -x "$LLAMA_BIN" ]; then
  echo "llama-server no encontrado en: $LLAMA_BIN" >&2
  exit 1
fi

exec "$LLAMA_BIN" "$@"
```


## `~/scripts/llm/start-ollama.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

source "$HOME/scripts/llm/env/llm-env.sh"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

exec ollama serve "$@"
```


## `~/scripts/llm/stop-llm.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

pkill -f 'vllm serve' 2>/dev/null || true
pkill -f 'llama-server' 2>/dev/null || true
pkill -f 'ollama serve' 2>/dev/null || true

if command -v docker >/dev/null 2>&1; then
  docker ps -q --filter "name=vllm" 2>/dev/null | xargs -r docker stop 2>/dev/null || true
  docker ps -q --filter "name=ollama" 2>/dev/null | xargs -r docker stop 2>/dev/null || true
  docker ps -q --filter "name=llama" 2>/dev/null | xargs -r docker stop 2>/dev/null || true
fi
```


## Instalación de los scripts

```bash
mkdir -p ~/scripts/llm/env
chmod +x ~/scripts/llm/start-vllm.sh
chmod +x ~/scripts/llm/start-llama.sh
chmod +x ~/scripts/llm/start-ollama.sh
chmod +x ~/scripts/llm/stop-llm.sh
```


## Aliases recomendados

Agrega esto a `~/.bashrc` o mejor a `~/.bash_aliases`:

```bash
alias vllm-start='~/scripts/llm/start-vllm.sh'
alias llama-start='~/scripts/llm/start-llama.sh'
alias ollama-start='~/scripts/llm/start-ollama.sh'
alias llm-stop='~/scripts/llm/stop-llm.sh'
```

Luego recarga:

```bash
source ~/.bashrc
```


## Siguiente validación

Después de eso, reinicia y comprueba:

```bash
systemctl get-default
systemctl list-unit-files --type=service | grep -E '(ollama|vllm|llama|docker|openclaw)'
ps aux | grep -E '(ollama|vllm|llama-server)' | grep -v grep
```

Si quieres, en el siguiente paso te puedo dar un **archivo `llm-env.sh` limpio y profesional**, con variables mínimas para Jetson, sin mezclar tokens ni paths de uso general.
<span style="display:none">[^10_10][^10_5][^10_6][^10_7][^10_8][^10_9]</span>

<div align="center">⁂</div>

[^10_1]: https://www.youtube.com/watch?v=2CG6AURrthk

[^10_2]: https://blog.csdn.net/qq_42533216/article/details/121489855

[^10_3]: https://www.reddit.com/r/Ubuntu/comments/hbloma/i_have_a_question_about_the_output_of_systemctl/

[^10_4]: https://stackoverflow.com/questions/49999068/docker-container-doesnt-start-after-reboot-with-enabling-systemd-script

[^10_5]: https://community.nethserver.org/t/systemctl-and-vendor-preset-disabled/18355

[^10_6]: https://www.simplified.guide/docker/service-manage

[^10_7]: https://www.reddit.com/r/linuxquestions/comments/mzgpiq/how_do_i_disable_a_systemd_user_service/

[^10_8]: https://man.archlinux.org/man/systemd.preset.5.en

[^10_9]: https://bbs.archlinux.org/viewtopic.php?id=194087

[^10_10]: http://anokun7.github.io/systemd-docker


---

# Ok, pero ahora tengo este inconveniente:

"""
jetson@jetson-orin:~\$ docker run --runtime nvidia -d \
--name qwen35-35b \
--restart no \
--network host \
--ipc host \
--shm-size 8g \
-e NVIDIA_VISIBLE_DEVICES=all \
ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
bash -c "cd /opt \&\& source venv/bin/activate \&\& \
vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
--gpu-memory-utilization 0.80 \
--enable-prefix-caching \
--reasoning-parser qwen3 \
--enable-auto-tool-choice \
--tool-call-parser qwen3_coder \
--host 0.0.0.0 \
--port 8000"
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory
jetson@jetson-orin:~\$ docker serve
docker: unknown command: docker serve

Run 'docker --help' for more information
jetson@jetson-orin:~\$ docker --help
Usage:  docker [OPTIONS] COMMAND
"""

El error es claro: **el cliente `docker` está instalado, pero el daemon no está levantado**, por eso no existe `/var/run/docker.sock`. En tu caso eso es coherente con la política de “arranque limpio”, pero para ejecutar ese contenedor de vLLM necesitas iniciar Docker manualmente antes de usar `docker run`.[^11_1][^11_2][^11_3]

## Qué pasó

`docker run` no es un comando que arranque el servicio; solo le habla al daemon. Si `dockerd` no está corriendo, el cliente no puede conectarse al socket UNIX y falla con ese mensaje. Además, `docker serve` no existe como subcomando de Docker, por eso te devolvió “unknown command”.[^11_4][^11_1]

## Qué debes hacer

Si quieres lanzar ese contenedor ahora mismo, primero levanta Docker manualmente:

```bash
sudo systemctl start docker
sudo systemctl start docker.socket
```

Después valida:

```bash
systemctl status docker --no-pager
systemctl status docker.socket --no-pager
ls -l /var/run/docker.sock
```

Cuando el socket exista, tu `docker run` debería poder conectarse.[^11_5][^11_1]

## Punto importante en tu arquitectura

Como tú querías un arranque limpio, lo correcto no es volver a habilitar Docker al boot, sino **arrancarlo solo cuando realmente vas a usar un contenedor**. Eso mantiene el sistema limpio tras cada reinicio y, al mismo tiempo, te permite usar esa imagen de vLLM cuando la necesites.[^11_2][^11_3]

## Comando recomendado para tu caso

Prueba esta secuencia:

```bash
sudo systemctl start docker.socket
sudo systemctl start docker
docker info
```

Si `docker info` responde correctamente, vuelve a lanzar tu contenedor.

## Corrección conceptual

Tu línea:

```bash
docker serve
```

debe eliminarse; no forma parte del flujo de Docker. El flujo correcto es:

1. levantar `docker.socket` o `docker.service`,
2. ejecutar `docker run`,
3. y luego detener Docker si quieres volver al estado limpio.[^11_3][^11_1]

## Recomendación final

Para tu modelo operativo, puedes dejar un alias manual tipo:

```bash
alias docker-on='sudo systemctl start docker.socket && sudo systemctl start docker'
alias docker-off='sudo systemctl stop docker && sudo systemctl stop docker.socket'
```

Así mantienes el control total: arranque limpio por defecto, y Docker solo cuando lo invoques explícitamente.[^11_2][^11_5]

Si quieres, el siguiente paso es que te adapte tus scripts `start-vllm.sh`, `start-llama.sh`, `start-ollama.sh` para que **primero verifiquen que Docker está activo**, o para que funcionen tanto en modo contenedor como en modo binario nativo.
<span style="display:none">[^11_10][^11_11][^11_6][^11_7][^11_8][^11_9]</span>

<div align="center">⁂</div>

[^11_1]: https://stackoverflow.com/questions/29349112/var-run-docker-sock-no-such-file-or-directory-are-you-trying-to-connect-to-a

[^11_2]: https://www.xurrent.com/blog/cannot-connect-to-the-docker-daemon

[^11_3]: https://stackoverflow.com/questions/28424014/dial-unix-var-run-docker-sock-no-such-file-or-directory-after-upgrading-to-lxc/32203550

[^11_4]: https://stackoverflow.com/questions/25372781/docker-error-var-run-docker-sock-no-such-file-or-directory

[^11_5]: https://blog.csdn.net/qq_42533216/article/details/121489855

[^11_6]: https://forums.developer.nvidia.com/t/permission-denied-while-trying-to-connect-to-the-docker-daemon-socket-at-unix-var-run-docker-sock/270360

[^11_7]: https://forums.docker.com/t/tutorial-solve-the-error-message-is-the-docker-daemon-running/145891

[^11_8]: https://github.com/docker/for-linux/issues/476

[^11_9]: https://stackoverflow.com/questions/33169122/docker-error-dial-unix-var-run-docker-sock-no-such-file-or-directory

[^11_10]: https://github.com/moby/moby/issues/22847

[^11_11]: https://stackoverflow.com/questions/44678725/cannot-connect-to-the-docker-daemon-at-unix-var-run-docker-sock-is-the-docker


---

# jetson@jetson-orin:~\$ docker run --runtime nvidia -d \

--name qwen35-35b \
--restart no \
--network host \
--ipc host \
--shm-size 8g \
-e NVIDIA_VISIBLE_DEVICES=all \
ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
bash -c "cd /opt \&\& source venv/bin/activate \&\& \
vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
--gpu-memory-utilization 0.80 \
--enable-prefix-caching \
--reasoning-parser qwen3 \
--enable-auto-tool-choice \
--tool-call-parser qwen3_coder \
--host 0.0.0.0 \
--port 8000"
docker: Error response from daemon: Conflict. The container name "/qwen35-35b" is already in use by container "fa6f4b43506e5ffd8bb1056fca4bf4054bf22464655832716231e356c48c2a1a". You have to remove (or rename) that container to be able to reuse that name.

Run 'docker run --help' for more information
jetson@jetson-orin:~\$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
jetson@jetson-orin:~\$ docker ps -a
CONTAINER ID   IMAGE                                                COMMAND                  CREATED          STATUS                      PORTS     NAMES
4a44e9ca8d8a   vllm/vllm-openai:v0.22.0-ubuntu2404                  "vllm serve google/g…"   31 minutes ago   Exited (0) 23 minutes ago             vllm
734cc7ce8f1c   ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin   "llama-server --hf-r…"   10 hours ago     Exited (137) 10 hours ago             nemotron-omni
fa6f4b43506e   ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin        "bash -c 'cd /opt \&\&…"   12 hours ago     Exited (143) 11 hours ago             qwen35-35b
27a58f28b8fa   nvcr.io/nvidia/vllm:26.05.post1-py3                  "/opt/nvidia/nvidia_…"   24 hours ago     Exited (137) 12 hours ago             vllm-openclaw
f90ead354b36   ghcr.io/open-webui/open-webui:main                   "bash start.sh"          31 hours ago     Exited (0) 12 hours ago               open-webui
jetson@jetson-orin:~\$

Eso ya es un conflicto distinto: **el nombre del contenedor `qwen35-35b` sigue reservado por un contenedor detenido**. `docker ps` solo muestra contenedores en ejecución, mientras que `docker ps -a` revela que `qwen35-35b` existe aunque esté en estado `Exited (143)`; por eso Docker no te deja reutilizar ese nombre hasta que lo borres o le cambies el nombre.[^12_1][^12_2][^12_3]

## Qué significa

Tu salida confirma que el contenedor con nombre `qwen35-35b` no está corriendo, pero sigue registrado en Docker como objeto existente. Cuando un contenedor se detiene, su nombre no se libera automáticamente; debes usar `docker rm` o crear uno nuevo con otro nombre.[^12_2][^12_3][^12_4]

## Qué hacer ahora

Si quieres reutilizar exactamente ese nombre, elimina el contenedor anterior:

```bash
docker rm qwen35-35b
```

Si prefieres conservarlo como referencia, crea el nuevo con otro nombre:

```bash
docker run --runtime nvidia -d \
  --name qwen35-35b-new \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.80 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"
```


## Qué conviene hacer en tu caso

Como tu objetivo es un sistema limpio y controlado, te conviene **limpiar los contenedores detenidos que ya no usarás** para evitar precisamente estas colisiones de nombres y residuos de ejecución. Los contenedores en estado `Exited` siguen ocupando nombre y siguen formando parte del inventario de Docker hasta que los eliminas.[^12_3][^12_5][^12_2]

## Limpieza recomendada

Para dejar el entorno ordenado:

```bash
docker rm vllm nemotron-omni qwen35-35b vllm-openclaw open-webui
```

Si alguno no existe ya, Docker te avisará, y puedes ignorar ese caso. Si además quieres limpiar todos los contenedores detenidos de una sola vez:

```bash
docker container prune
```

Eso borra contenedores parados y libera nombres; úsalo solo si no necesitas conservar ninguno.[^12_5][^12_2]

## Regla práctica para tu flujo

Para tu arquitectura, lo más sano es:

- usar nombres únicos por pipeline o por modelo;
- borrar contenedores que ya no vas a reutilizar;
- no depender de contenedores “fantasma” detenidos como parte de tu estado normal de trabajo.

Eso mantiene coherencia con tu idea de **arranque limpio** y evita que un contenedor antiguo bloquee una nueva ejecución.[^12_4][^12_2][^12_3]

Si quieres, te puedo dar ahora mismo un **comando seguro de limpieza selectiva** para tus contenedores actuales, conservando solo los que te interese mantener.
<span style="display:none">[^12_10][^12_6][^12_7][^12_8][^12_9]</span>

<div align="center">⁂</div>

[^12_1]: https://stackoverflow.com/questions/31697828/docker-name-is-already-in-use-by-container

[^12_2]: https://stackoverflow.com/questions/68962063/you-have-to-remove-or-rename-that-container-to-be-able-to-reuse-that-name

[^12_3]: https://www.baeldung.com/ops/docker-name-already-in-use

[^12_4]: https://hamy.xyz/blog/2022-11-docker-error-container-name-is-already-in-use

[^12_5]: https://forums.docker.com/t/dangling-container-name-problem-name-already-in-use-by-container/20199

[^12_6]: https://forums.docker.com/t/container-name-already-in-use/140176

[^12_7]: https://www.dash0.com/faq/how-to-fix-name-already-in-use-by-container-in-docker

[^12_8]: https://labex.io/tutorials/docker-how-to-handle-container-name-already-in-use-error-in-docker-415733

[^12_9]: https://www.youtube.com/watch?v=GWVNUzEavAY

[^12_10]: https://oneuptime.com/blog/post/2026-01-25-fix-docker-container-name-conflict-errors/view


---

# Ok, pero es el mismo contenedor, lo que quiero es correrlo

Sí: en ese caso no debes volver a usar `docker run` porque el contenedor **ya existe**; lo correcto es arrancarlo con `docker start qwen35-35b`.[^13_1][^13_2]

## Qué significa el error

`docker run` crea un contenedor nuevo, por eso choca con el nombre si ya hay uno registrado con ese mismo nombre, aunque esté detenido. Para reusar el contenedor existente, Docker espera `docker start`, que solo arranca un contenedor previamente creado y parado.[^13_3][^13_4][^13_2][^13_1]

## Comando correcto

Prueba esto:

```bash
docker start qwen35-35b
```

Si quieres ver su salida interactiva en primer plano, usa:

```bash
docker start -ai qwen35-35b
```

Eso es útil si el contenedor se para de inmediato y quieres observar por qué.[^13_5][^13_2]

## Verificación útil

Después de arrancarlo, revisa:

```bash
docker ps
docker logs -f qwen35-35b
```

Si el contenedor vuelve a salir, los logs te dirán si el problema está en el modelo, en el comando de `vllm serve`, o en el entorno dentro del contenedor.[^13_2]

## Si quieres reiniciarlo limpio

Si lo que buscas es volver a levantarlo exactamente como fue creado originalmente, primero puedes pararlo si está corriendo y luego iniciar el existente:

```bash
docker stop qwen35-35b
docker start qwen35-35b
```

No uses `docker rm` si tu intención es conservar ese mismo contenedor y solo correrlo otra vez.[^13_1][^13_2]

## Regla práctica

- `docker run` = crea uno nuevo y lo ejecuta.
- `docker start` = ejecuta uno ya existente.
- `docker rm` = lo elimina.

En tu caso, el contenedor ya está creado, así que la ruta correcta es `docker start qwen35-35b`.[^13_4][^13_2][^13_1]

Si quieres, te doy ahora un mini flujo de tres comandos para **arrancar, monitorear y parar** ese contenedor sin volver a caer en el conflicto de nombre.
<span style="display:none">[^13_10][^13_6][^13_7][^13_8][^13_9]</span>

<div align="center">⁂</div>

[^13_1]: https://stackoverflow.com/questions/39400284/starting-a-container-that-was-already-started-and-stoppped

[^13_2]: https://stackoverflow.com/questions/36947078/docker-start-a-container-after-stopping

[^13_3]: https://stackoverflow.com/questions/31697828/docker-name-is-already-in-use-by-container

[^13_4]: https://www.baeldung.com/ops/docker-name-already-in-use

[^13_5]: https://stackoverflow.com/questions/61437372/how-to-start-an-existing-docker-container-with-displaying-the-output

[^13_6]: https://www.oreateai.com/blog/docker-start-vs-docker-run-unpacking-the-nuances-for-smoother-deployments/1531b5405de80a7aadee412ab78f6c38

[^13_7]: https://qiita.com/twinbee/items/5f55ba3c852140ccf6d0

[^13_8]: https://stackoverflow.com/questions/44731451/how-to-run-a-docker-container-if-not-already-running/44739847

[^13_9]: https://www.dash0.com/faq/how-to-fix-name-already-in-use-by-container-in-docker

[^13_10]: https://oneuptime.com/blog/post/2026-01-25-fix-docker-container-name-conflict-errors/view


---

# Ok, pero al correr "docker start qwen35-35b" corre con toda la configuracion descrita?

"""
jetson@jetson-orin:~\$ docker run --runtime nvidia -d \
--name qwen35-35b \
--restart no \
--network host \
--ipc host \
--shm-size 8g \
-e NVIDIA_VISIBLE_DEVICES=all \
ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
bash -c "cd /opt \&\& source venv/bin/activate \&\& \
vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
--gpu-memory-utilization 0.80 \
--enable-prefix-caching \
--reasoning-parser qwen3 \
--enable-auto-tool-choice \
--tool-call-parser qwen3_coder \
--host 0.0.0.0 \
--port 8000"

"""

Sí, **pero con una precisión importante**: `docker start qwen35-35b` sí vuelve a arrancar **ese mismo contenedor existente** con su configuración original de creación, incluyendo red, `--ipc`, `--shm-size`, variables de entorno, y el comando que quedó guardado al crearlo. Lo que **no** hace `docker start` es aplicar nuevas flags escritas en un nuevo `docker run`; esas opciones solo se fijan en el momento de `docker run` o `docker create`.[^14_1][^14_2][^14_3][^14_4]

## En tu caso

Como el contenedor `qwen35-35b` ya fue creado con esta orden:

- `--runtime nvidia`
- `--network host`
- `--ipc host`
- `--shm-size 8g`
- `-e NVIDIA_VISIBLE_DEVICES=all`
- y el `bash -c "cd /opt && source venv/bin/activate && vllm serve ..."`

entonces `docker start qwen35-35b` debería relanzarlo con **esa misma configuración original**. Eso significa que no necesitas repetir todo el `docker run` para volver a ejecutar el mismo contenedor, siempre que no quieras cambiar parámetros.[^14_2][^14_3][^14_4][^14_1]

## Lo que sí debes recordar

Si el contenedor fue creado con un comando que al arrancar lanza `vllm serve`, entonces `docker start qwen35-35b` reejecutará ese flujo tal como fue definido originalmente. Pero si quieres cambiar cualquier cosa —por ejemplo el modelo, el puerto, la memoria GPU, el nombre del contenedor o el comando interno— entonces no basta con `docker start`: tendrías que crear un contenedor nuevo.[^14_3][^14_4][^14_1][^14_2]

## Comando correcto para probar

```bash
docker start qwen35-35b
```

Si quieres ver la salida en la terminal:

```bash
docker start -ai qwen35-35b
```

Y si quieres verificar que volvió a quedar arriba:

```bash
docker ps
docker logs -f qwen35-35b
```


## Resumen operativo

- `docker start qwen35-35b` = reanuda el contenedor existente con su configuración guardada.[^14_4][^14_1]
- `docker run ... --name qwen35-35b` = intenta crear uno nuevo y por eso choca con el nombre.[^14_5][^14_6]
- Si quieres exactamente la misma ejecución, usa `docker start`.
- Si quieres cambiar parámetros, elimina y recrea el contenedor.[^14_2][^14_3]

Si quieres, el siguiente paso es que revisemos **por qué ese contenedor termina en `Exited (143)`** y cómo dejarlo estable en Jetson para que no se cierre apenas arranca.
<span style="display:none">[^14_10][^14_11][^14_7][^14_8][^14_9]</span>

<div align="center">⁂</div>

[^14_1]: https://www.youtube.com/watch?v=wCrrjrJ_zRU

[^14_2]: https://stackoverflow.com/questions/41067032/how-to-stop-relaunch-docker-container-without-losing-the-changes

[^14_3]: https://stackoverflow.com/questions/32353055/how-to-start-a-stopped-docker-container-with-a-different-command

[^14_4]: https://linuxcommandlibrary.com/man/docker-container-start

[^14_5]: https://stackoverflow.com/questions/31697828/docker-name-is-already-in-use-by-container

[^14_6]: https://www.baeldung.com/ops/docker-name-already-in-use

[^14_7]: https://openillumi.com/en/en-docker-run-start-difference-lifecycle/

[^14_8]: https://www.dash0.com/faq/how-to-start-a-docker-container

[^14_9]: https://stackoverflow.com/questions/33626846/docker-run-container-how-to-rerun

[^14_10]: https://forums.docker.com/t/loosing-modifications-after-rerunning-container/123003

[^14_11]: https://github.com/moby/moby/issues/15725

