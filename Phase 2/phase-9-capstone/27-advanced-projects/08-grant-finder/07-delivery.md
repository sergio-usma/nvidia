# Funding Finder - Email & Google Drive Delivery

## Overview

Once a proposal is complete, the delivery system packages everything and sends it via email while also organizing files in Google Drive.

## Email Delivery

### SMTP Configuration

```python
#!/usr/bin/env python3
"""
Email Delivery System
Sends proposals via email with ZIP attachment
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "recipient": "sergioandresusma@hotmail.com",
    "sender": os.getenv("SMTP_USER", "")
}


class EmailDelivery:
    """Handles email delivery of proposals"""
    
    def __init__(self):
        self.smtp_host = CONFIG["smtp_host"]
        self.smtp_port = CONFIG["smtp_port"]
        self.smtp_user = CONFIG["smtp_user"]
        self.smtp_password = CONFIG["smtp_password"]
        self.recipient = CONFIG["recipient"]
    
    def create_zip_archive(self, proposal_dir: Path, opportunity_id: str) -> Path:
        """Create ZIP file with all proposal documents"""
        
        zip_path = proposal_dir.parent / f"{opportunity_id}_proposal.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from proposal directory
            for file_path in proposal_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.name
                    zipf.write(file_path, arcname)
                    logger.info(f"Added to ZIP: {arcname}")
        
        logger.info(f"Created ZIP: {zip_path}")
        return zip_path
    
    def create_email_content(self, proposal_data: Dict, opportunity: Dict) -> tuple:
        """Create email subject and body"""
        
        # Subject
        subject = f"PROPUESTA: {proposal_data.get('project_title', 'Project')} - {opportunity.get('source', 'Funding')}"
        
        # Body
        budget = proposal_data.get('budget', {})
        total_budget = budget.get('total_budget', 'N/A')
        
        body = f"""🦸 FONDO DE FINANCIAMIENTO - PROPUESTA GENERADA

Estimado/a,

Se ha generado automáticamente una propuesta completa para la oportunidad de financiamiento:

📋 INFORMACIÓN DE LA OPORTUNIDAD
─────────────────────────────────
• Título: {opportunity.get('title', 'N/A')}
• Fuente: {opportunity.get('source', 'N/A')}
• Fecha límite: {opportunity.get('deadline', 'N/A')}
• Presupuesto: {opportunity.get('budget', 'N/A')}
• Categoría: {opportunity.get('category', 'N/A')}

📄 INFORMACIÓN DEL PROYECTO
─────────────────────────────────
• Título del proyecto: {proposal_data.get('project_title', 'N/A')}
• Visión: {proposal_data.get('vision', 'N/A')[:200]}...
• Objetivos: {len(proposal_data.get('objectives', []))} objetivos definidos
• Duración: {proposal_data.get('duration_months', 'N/A')} meses
• Presupuesto total solicitado: {total_budget}

📊 RESUMEN DE LA PROPUESTA
─────────────────────────────────
• Metodología técnica: {'✓ Completada' if proposal_data.get('technical') else '✗ Pendiente'}
• Presupuesto detallado: {'✓ Completado' if proposal_data.get('budget') else '✗ Pendiente'}
• Cumplimiento de requisitos: {'✓ Aprobado' if proposal_data.get('compliance', {}).get('eligible') else '✗ Revisar'}

📎 DOCUMENTOS ADJUNTOS
─────────────────────────────────
• Propuesta completa en formato ZIP
• Todos los anexos y requisitos
• Documentos originales de la convocatoria

⚠️ NOTAS IMPORTANTES
─────────────────────────────────
• Esta propuesta fue generada automáticamente usando IA local
• Por favor revise todos los documentos antes de enviar
• Verifique que cumple con todos los requisitos específicos
• Asegure los tiempos de envío

💾 ARCHIVOS INCLUIDOS
─────────────────────────────────
• Proposal_{opportunity_id}.docx - Propuesta principal
• Budget_{opportunity_id}.xlsx - Presupuesto detallado
• Compliance_{opportunity_id}.pdf - Cumplimiento de requisitos
• Timeline_{opportunity_id}.pdf - Cronograma del proyecto
• * Todos los documentos de la convocatoria

El archivo ZIP adjunto contiene todos los documentos necesarios.

Atentamente,
🤖 Sistema de Generación Automática de Propuestas
NVIDIA Jetson AGX Orin - Funding Finder
"""
        
        return subject, body
    
    def send_email(self, proposal_data: Dict, opportunity: Dict, 
                   zip_path: Path) -> bool:
        """Send email with proposal attached"""
        
        subject, body = self.create_email_content(proposal_data, opportunity)
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.recipient
            msg['Subject'] = subject
            
            # Attach body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach ZIP file
            with open(zip_path, 'rb') as f:
                part = MIMEBase('application', 'zip')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{zip_path.name}"'
                )
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {self.recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
```

## Google Drive Delivery

### Drive API Integration

```python
#!/usr/bin/env python3
"""
Google Drive Delivery System
Uploads proposals to Google Drive with folder structure
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "credentials_file": os.getenv(
        "GOOGLE_CREDENTIALS",
        "/opt/funding-finder/config/credentials.json"
    ),
    "root_folder_id": os.getenv("DRIVE_ROOT_FOLDER", "")
}


class DriveDelivery:
    """Handles Google Drive uploads"""
    
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            CONFIG["credentials_file"],
            scopes=[
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def create_folder(self, name: str, parent_id: str = None) -> str:
        """Create a folder in Google Drive"""
        
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = self.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        folder_id = folder.get('id')
        logger.info(f"Created folder: {name} ({folder_id})")
        return folder_id
    
    def upload_file(self, file_path: Path, folder_id: str, 
                    filename: str = None) -> str:
        """Upload a file to Google Drive"""
        
        if filename is None:
            filename = file_path.name
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(str(file_path), resumable=True)
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        logger.info(f"Uploaded: {filename} ({file_id})")
        return file_id
    
    def create_proposal_folder(self, opportunity: Dict, proposal_data: Dict) -> str:
        """Create organized folder structure for proposal"""
        
        # Create main folder with proposal title
        proposal_title = proposal_data.get("project_title", "Proposal")
        safe_title = "".join(c for c in proposal_title[:50] if c.isalnum() or c in " -_")
        
        # Get or create root folder
        root_id = CONFIG["root_folder_id"]
        if not root_id:
            root_id = self.create_folder("Funding Proposals")
        
        # Create dated folder
        date_str = datetime.now().strftime("%Y-%m-%d")
        main_folder = self.create_folder(
            f"{date_str} - {safe_title}",
            root_id
        )
        
        # Create subfolders
        offer_folder = self.create_folder("01_Offer_Documents", main_folder)
        proposal_folder = self.create_folder("02_Proposal_Documents", main_folder)
        
        return {
            "main": main_folder,
            "offer": offer_folder,
            "proposal": proposal_folder
        }
    
    def upload_proposal(self, proposal_dir: Path, opportunity: Dict,
                       proposal_data: Dict) -> Dict:
        """Upload complete proposal to Google Drive"""
        
        # Create folder structure
        folders = self.create_proposal_folder(opportunity, proposal_data)
        
        # Upload offer documents
        offer_dir = proposal_dir / "offer"
        if offer_dir.exists():
            for file_path in offer_dir.rglob("*"):
                if file_path.is_file():
                    self.upload_file(file_path, folders["offer"])
        
        # Upload proposal documents
        proposal_files_dir = proposal_dir / "proposal"
        if proposal_files_dir.exists():
            for file_path in proposal_files_dir.rglob("*"):
                if file_path.is_file():
                    self.upload_file(file_path, folders["proposal"])
        
        # Create summary document
        summary_content = self.create_summary(opportunity, proposal_data)
        summary_path = proposal_dir / "proposal" / "SUMMARY.txt"
        summary_path.write_text(summary_content)
        self.upload_file(summary_path, folders["proposal"], "SUMMARY.txt")
        
        logger.info(f"Proposal uploaded to Drive: {folders['main']}")
        
        return folders
    
    def create_summary(self, opportunity: Dict, proposal_data: Dict) -> str:
        """Create summary document"""
        
        summary = f"""
================================================================================
FONDO DE FINANCIAMIENTO - RESUMEN DE PROPUESTA
================================================================================

FECHA DE GENERACIÓN: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

================================================================================
INFORMACIÓN DE LA OPORTUNIDAD
================================================================================
ID: {opportunity.get('id', 'N/A')}
Título: {opportunity.get('title', 'N/A')}
Fuente: {opportunity.get('source', 'N/A')}
URL: {opportunity.get('url', 'N/A')}
Fecha límite: {opportunity.get('deadline', 'N/A')}
Presupuesto: {opportunity.get('budget', 'N/A')}
Categoría: {opportunity.get('category', 'N/A')}
Idioma: {opportunity.get('language', 'N/A')}

================================================================================
PROYECTO PROPUESTO
================================================================================
Título: {proposal_data.get('project_title', 'N/A')}
Visión: {proposal_data.get('vision', 'N/A')}
Duración: {proposal_data.get('duration_months', 'N/A')} meses

Objetivos:
{chr(10).join(f"  {i+1}. {obj}" for i, obj in enumerate(proposal_data.get('objectives', [])))}

Resultados esperados:
{chr(10).join(f"  {i+1}. {res}" for i, res in enumerate(proposal_data.get('outcomes', [])))}

Beneficiarios: {proposal_data.get('beneficiaries', 'N/A')}

================================================================================
PRESUPUESTO
================================================================================
Total: {proposal_data.get('budget', {}).get('total_budget', 'N/A')}
{p proposal_data.get('budget', {}).get('budget_justification', '')}

================================================================================
CUMPLIMIENTO
================================================================================
Elegible: {proposal_data.get('compliance', {}).get('eligible', 'N/A')}
{poprosal_data.get('compliance', {}).get('eligibility_notes', '')}

================================================================================
ESTADO
================================================================================
Estado del proyecto: {proposal_data.get('status', 'N/A')}
Fecha de envío: {datetime.now().isoformat()}

================================================================================
Este documento fue generado automáticamente por Funding Finder
Sistema de Generación Automática de Propuestas - NVIDIA Jetson AGX Orin
================================================================================
"""
        return summary


# Document generators
class DocumentGenerator:
    """Generates proposal documents"""
    
    def generate_proposal_docx(self, proposal_data: Dict, output_path: Path):
        """Generate Word document proposal"""
        
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Title
        title = doc.add_heading(proposal_data.get('project_title', 'Project Proposal'), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Vision
        doc.add_heading('Vision', level=1)
        doc.add_paragraph(proposal_data.get('vision', ''))
        
        # Objectives
        doc.add_heading('Objectives', level=1)
        for obj in proposal_data.get('objectives', []):
            doc.add_paragraph(obj, style='List Bullet')
        
        # Outcomes
        doc.add_heading('Expected Outcomes', level=1)
        for outcome in proposal_data.get('outcomes', []):
            doc.add_paragraph(outcome, style='List Bullet')
        
        # Save
        doc.save(str(output_path))
        logger.info(f"Generated DOCX: {output_path}")
    
    def generate_budget_xlsx(self, proposal_data: Dict, output_path: Path):
        """Generate Excel budget"""
        
        import pandas as pd
        
        budget = proposal_data.get('budget', {})
        
        # Create budget DataFrame
        items = []
        
        for person in budget.get('personnel', []):
            total = person.get('monthly_rate', 0) * person.get('months', 0)
            items.append({
                'Category': 'Personnel',
                'Item': person.get('role', ''),
                'Monthly Rate': person.get('monthly_rate', 0),
                'Months': person.get('months', 0),
                'Total': total
            })
        
        for item in budget.get('equipment', []):
            items.append({
                'Category': 'Equipment',
                'Item': item.get('description', ''),
                'Quantity': item.get('quantity', 1),
                'Unit Cost': item.get('unit_cost', 0),
                'Total': item.get('quantity', 1) * item.get('unit_cost', 0)
            })
        
        # Add totals row
        total_budget = sum(item['Total'] for item in items)
        items.append({
            'Category': 'TOTAL',
            'Item': '',
            'Monthly Rate': '',
            'Months': '',
            'Total': total_budget
        })
        
        # Save to Excel
        df = pd.DataFrame(items)
        df.to_excel(str(output_path), index=False)
        logger.info(f"Generated XLSX: {output_path}")
```

## Complete Delivery Workflow

```python
class DeliveryOrchestrator:
    """Orchestrates email and Drive delivery"""
    
    def __init__(self):
        self.email = EmailDelivery()
        self.drive = DriveDelivery()
        self.doc_gen = DocumentGenerator()
    
    def deliver_proposal(self, opportunity_id: str, proposal_data: Dict) -> Dict:
        """Complete delivery process"""
        
        # Get opportunity data
        response = requests.get(f"http://localhost:8081/queue/{opportunity_id}")
        opportunity = response.json()
        
        # Create output directory
        output_dir = Path(f"/opt/funding-finder/output/{opportunity_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate documents
        self.doc_gen.generate_proposal_docx(
            proposal_data,
            output_dir / "proposal.docx"
        )
        
        self.doc_gen.generate_budget_xlsx(
            proposal_data,
            output_dir / "budget.xlsx"
        )
        
        # Copy offer documents
        offer_source = Path(f"/opt/funding-finder/data/documents/{opportunity_id}")
        if offer_source.exists():
            offer_dest = output_dir / "offer"
            offer_dest.mkdir(exist_ok=True)
            import shutil
            shutil.copytree(offer_source, offer_dest, dirs_exist_ok=True)
        
        # Create ZIP
        zip_path = self.email.create_zip_archive(output_dir, opportunity_id)
        
        # Send email
        email_sent = self.email.send_email(proposal_data, opportunity, zip_path)
        
        # Upload to Drive
        drive_folders = self.drive.upload_proposal(output_dir, opportunity, proposal_data)
        
        return {
            "email_sent": email_sent,
            "drive_folder": drive_folders["main"],
            "zip_file": str(zip_path)
        }
```

## API Endpoint

```python
@app.route("/delivery/send", methods=["POST"])
def deliver_proposal():
    """Trigger proposal delivery"""
    data = request.get_json()
    opportunity_id = data.get("opportunity_id")
    
    orchestrator = DeliveryOrchestrator()
    result = orchestrator.deliver_proposal(opportunity_id, proposal_data)
    
    return jsonify(result)
```

## Next Steps

- [08-installation](./08-installation.md) - Complete installation guide
