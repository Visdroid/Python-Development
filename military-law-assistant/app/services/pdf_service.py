import os
import time
import logging
import requests
import pdfplumber
from pathlib import Path
from typing import List, Dict, Optional
from app.military_law_assistant_config import Config

config = Config()
logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        self.documents_dir = config.DOCUMENTS_FOLDER
        self.available_resources = []
        self._init_resources()
        self.init_pdfs()

    def _init_resources(self):
        self.resources = [
            # Constitutional Law
            {
                "url": "https://www.justice.gov.za/legislation/constitution/SAConstitution-web-eng.pdf",
                "path": "constitution.pdf",
                "name": "Constitution of South Africa, 1996",
                "category": "constitutional"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201506/38859rg10798gon608.pdf",
                "path": "bill_of_rights.pdf",
                "name": "Bill of Rights (Constitution Chapter 2)",
                "category": "constitutional"
            },
            
            # Criminal Law and Procedure
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201501/38316act51of1977s.pdf",
                "path": "criminal_procedure_act.pdf",
                "name": "Criminal Procedure Act 51 of 1977",
                "category": "criminal"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a32-07.pdf",
                "path": "sexual_offences_act.pdf",
                "name": "Sexual Offences Act 32 of 2007",
                "category": "criminal"
            },
            
            # Investigation and Intelligence
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a65-02.pdf",
                "path": "intelligence_services_act.pdf",
                "name": "Intelligence Services Act 65 of 2002",
                "category": "investigation"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a37-13.pdf",
                "path": "dna_act.pdf",
                "name": "Criminal Law (Forensic Procedures) Amendment Act 37 of 2013",
                "category": "investigation"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a26-00.pdf",
                "path": "protected_disclosures_act.pdf",
                "name": "Protected Disclosures Act 26 of 2000",
                "category": "investigation"
            },
            
            # Cyber and Digital Laws
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/202105/44351gon1013.pdf",
                "path": "cybercrimes_act.pdf",
                "name": "Cybercrimes Act 19 of 2020",
                "category": "cyber"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a25-02.pdf",
                "path": "electronic_communications_act.pdf",
                "name": "Electronic Communications and Transactions Act 25 of 2002",
                "category": "cyber"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a70-02.pdf",
                "path": "rica_act.pdf",
                "name": "Regulation of Interception of Communications Act 70 of 2002",
                "category": "cyber"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a4-13.pdf",
                "path": "popi_act.pdf",
                "name": "Protection of Personal Information Act 4 of 2013",
                "category": "cyber"
            },
            
            # Financial and Fraud Laws
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a12-04.pdf",
                "path": "prevention_of_corruption_act.pdf",
                "name": "Prevention and Combating of Corrupt Activities Act 12 of 2004",
                "category": "financial"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a38-01.pdf",
                "path": "fica_act.pdf",
                "name": "Financial Intelligence Centre Act 38 of 2001",
                "category": "financial"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a121-98.pdf",
                "path": "poca_act.pdf",
                "name": "Prevention of Organised Crime Act 121 of 1998",
                "category": "financial"
            },
            
            # Social Media and Internet Laws
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a3-09.pdf",
                "path": "films_publications_act.pdf",
                "name": "Films and Publications Amendment Act 3 of 2009",
                "category": "internet"
            },
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a36-05.pdf",
                "path": "electronic_comm_act.pdf",
                "name": "Electronic Communications Act 36 of 2005",
                "category": "internet"
            },
            
            # Military and Defense
            {
                "url": "https://www.gov.za/sites/default/files/gcis_document/201409/a42-02.pdf",
                "path": "defence_act.pdf",
                "name": "Defence Act 42 of 2002",
                "category": "military"
            }
        ]

    def _download_pdf(self, resource: Dict) -> bool:
        file_path = self.documents_dir / resource["path"]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for attempt in range(3):  # Increased to 3 attempts
            try:
                with requests.get(resource["url"], headers=headers, stream=True, timeout=30) as r:  # Increased timeout
                    r.raise_for_status()
                    
                    # More robust content type checking
                    content_type = r.headers.get('content-type', '')
                    if 'pdf' not in content_type and 'octet-stream' not in content_type:
                        raise ValueError(f"Unexpected content type: {content_type}")
                    
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:  # filter out keep-alive chunks
                                f.write(chunk)
                    
                    # More thorough file validation
                    if not file_path.exists() or file_path.stat().st_size < 2048:  # Increased minimum size
                        raise ValueError("Downloaded file is too small or corrupted")
                    
                    # Verify PDF magic number
                    with open(file_path, 'rb') as f:
                        if f.read(4) != b'%PDF':
                            raise ValueError("Downloaded file is not a valid PDF")
                    
                    return True
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {resource['name']}: {str(e)}")
                if file_path.exists():
                    file_path.unlink()
                time.sleep(2 ** attempt)  # Exponential backoff
                
        logger.error(f"Failed to download {resource['name']} after 3 attempts")
        return False

    def init_pdfs(self) -> None:
        self.documents_dir.mkdir(exist_ok=True, parents=True)
        success = 0
        
        for resource in self.resources:
            file_path = self.documents_dir / resource["path"]
            
            # More thorough file validation
            if file_path.exists() and file_path.stat().st_size > 2048:
                try:
                    with open(file_path, 'rb') as f:
                        if f.read(4) == b'%PDF':
                            self.available_resources.append(resource)
                            success += 1
                            logger.info(f"Using existing valid PDF: {resource['name']}")
                            continue
                        else:
                            logger.warning(f"Existing file is not a valid PDF: {resource['name']}")
                            file_path.unlink()
                except Exception as e:
                    logger.warning(f"Error checking existing PDF {resource['name']}: {str(e)}")
                    file_path.unlink()
                
            if self._download_pdf(resource):
                self.available_resources.append(resource)
                success += 1
                logger.info(f"Successfully loaded: {resource['name']}")
            else:
                logger.error(f"Failed to load: {resource['name']}")
        
        logger.info(f"Loaded {success}/{len(self.resources)} legal documents")
        if success < len(self.resources):
            missing = [r['name'] for r in self.resources if r not in self.available_resources]
            logger.warning(f"Missing documents: {', '.join(missing)}")

    def extract_text(self, categories: Optional[List[str]] = None, max_pages: int = 50) -> str:
        if not self.available_resources:
            return "No legal documents available"
            
        texts = []
        for resource in [r for r in self.available_resources 
                        if not categories or r["category"] in categories]:
            try:
                file_path = self.documents_dir / resource["path"]
                if not file_path.exists():
                    continue
                    
                with pdfplumber.open(file_path) as pdf:
                    doc_text = f"\n=== {resource['name']} ===\n"
                    page_count = min(len(pdf.pages), max_pages)
                    for i in range(page_count):
                        try:
                            if text := pdf.pages[i].extract_text():
                                doc_text += f"{text}\n"
                        except Exception as e:
                            logger.warning(f"Error reading page {i+1} of {resource['name']}: {str(e)}")
                            continue
                    texts.append(doc_text)
            except Exception as e:
                logger.error(f"Error processing {resource['name']}: {str(e)}")
        
        return "\n".join(texts) if texts else "No matching legal text found"

    def get_available_resources(self) -> List[Dict]:
        return [
            {
                "name": r["name"],
                "category": r["category"],
                "path": str(self.documents_dir / r["path"]),
                "size": (self.documents_dir / r["path"]).stat().st_size if (self.documents_dir / r["path"]).exists() else 0,
                "status": "Available" if (self.documents_dir / r["path"]).exists() else "Missing",
                "url": r["url"]
            }
            for r in self.resources
        ]

    def get_resource_by_category(self, category: str) -> List[Dict]:
        return [r for r in self.available_resources if r["category"] == category]

    def refresh_resources(self) -> None:
        """Force re-download of all resources"""
        logger.info("Initiating full refresh of legal documents")
        self.available_resources = []
        for file in self.documents_dir.glob("*.pdf"):
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"Error deleting {file.name}: {str(e)}")
        self.init_pdfs()
        logger.info("Legal documents refresh completed")

    def get_missing_resources(self) -> List[Dict]:
        """Return list of resources that failed to download"""
        return [r for r in self.resources if r not in self.available_resources]