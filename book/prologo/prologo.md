# Prólogo

Existe un momento preciso en el que una pieza de hardware deja de ser un componente técnico y se convierte en una posibilidad. Para mí, ese momento ocurrió la tarde en que encendí por primera vez el NVIDIA Jetson AGX Orin 64GB y vi cómo un modelo de lenguaje de siete mil millones de parámetros respondía a mis preguntas —sin conexión a Internet, sin servidores en la nube, sin latencias impredecibles— en tiempo real, desde un dispositivo del tamaño de una novela de bolsillo que cabe en la palma de mi mano.

No era un experimento de laboratorio. Era producción real.

Ese día comprendí que algo fundamental había cambiado en el mundo de la inteligencia artificial. La IA ya no pertenece exclusivamente a los centros de datos de las grandes corporaciones. Ya no requiere una tarjeta de crédito vinculada a una API de terceros ni depende de una conexión estable a la nube. Con el hardware correcto y el conocimiento adecuado, cualquier desarrollador, ingeniero o emprendedor puede desplegar un stack de IA completo —inferencia de modelos de lenguaje, visión por computadora, síntesis de voz, automatización de flujos de trabajo— en su propio entorno, bajo su propio control, a una fracción del costo operativo de los servicios en la nube.

El Jetson AGX Orin 64GB es el dispositivo más poderoso que NVIDIA ha fabricado para computación en el borde (*edge computing*). Su arquitectura Ampere con 2,048 núcleos CUDA, 64 núcleos Tensor, 64 GB de memoria unificada y un consumo máximo de 60 W lo posiciona en una categoría propia: no es un microcontrolador, no es una Raspberry Pi potenciada; es un servidor de IA compacto capaz de ejecutar modelos de 70 mil millones de parámetros cuantizados, pipelines de visión artificial en tiempo real y agentes de IA autónomos, todo de forma simultánea.

Pero con gran poder viene una curva de aprendizaje considerable.

Cuando comencé a documentar mi propio proceso de puesta en marcha del Jetson con JetPack 7.2, descubrí que la información disponible estaba fragmentada en docenas de repositorios, foros, hilos de Reddit y documentación oficial dispersa. Cada tutorial asumía conocimientos previos distintos. Los comandos de versiones anteriores (JP 6.2, JP 5.x) no siempre funcionaban en JP 7.2. Los cambios de Ubuntu 22.04 a Ubuntu 24.04, de Python 3.10 a Python 3.12 y de CUDA 12.6 a CUDA 13.2.1 introducían incompatibilidades silenciosas que tardaban horas —a veces días— en diagnosticarse.

Decidí escribir el libro que yo hubiera necesitado.

Este libro es el resultado de cientos de horas de verificación, prueba y depuración sobre hardware real —un Jetson AGX Orin 64GB ejecutando JetPack 7.2 (L4T r39.2, Ubuntu 24.04, CUDA 13.2.1, Python 3.12)— y de la convicción de que la documentación técnica debe ser honesta sobre sus condiciones de validez. Cada comando que aparece en estas páginas fue ejecutado, verificado y documentado con su salida esperada. Cuando algo puede fallar, se explica por qué falla y cómo solucionarlo.

El libro está estructurado para acompañarle desde el primer encendido hasta el despliegue de proyectos de producción complejos: una agencia de IA autónoma con presencia web, un pipeline de automatización de contenido en video, un sistema RAG para documentos empresariales, un asistente de voz completamente offline. No son prototipos académicos. Son sistemas funcionales que puede adaptar y desplegar en su propio contexto.

Si usted es desarrollador, ingeniero de inteligencia artificial, investigador o emprendedor tecnológico, y tiene un Jetson AGX Orin 64GB en sus manos —o planea adquirir uno—, este libro le llevará desde cero hasta producción con la certeza de que cada paso ha sido verificado en la plataforma exacta que usted utilizará.

La inteligencia artificial en el borde no es el futuro. Es hoy. Y está en sus manos.

---

*Sergio Von Usma*
*Julio de 2026*
