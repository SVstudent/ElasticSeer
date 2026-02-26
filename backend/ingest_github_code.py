#!/usr/bin/env python3
"""
Ingest code from GitHub repository into Elasticsearch
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from github import Github
import logging
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Configuration - read from settings (which loads from .env)
GITHUB_TOKEN = settings.github_token
GITHUB_OWNER = settings.github_owner
GITHUB_REPO = settings.github_repo
ES_URL = settings.elasticsearch_url
ES_API_KEY = settings.elasticsearch_api_key


def detect_language(filename):
    """Detect programming language from filename"""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.jsx': 'javascript',
        '.java': 'java',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'csharp',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rs': 'rust'
    }
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return 'unknown'


def ingest_code():
    """Ingest code from GitHub repository"""
    logger.info("="*70)
    logger.info("GitHub Code Ingestion")
    logger.info("="*70)
    
    # Connect to GitHub
    logger.info(f"\n📦 Connecting to GitHub...")
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        logger.info(f"  ✓ Authenticated as: {user.login}")
    except Exception as e:
        logger.error(f"  ❌ GitHub authentication failed: {e}")
        return False
    
    # Get repository
    try:
        repo = g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")
        logger.info(f"  ✓ Repository: {repo.full_name}")
        logger.info(f"  ✓ Default branch: {repo.default_branch}")
    except Exception as e:
        logger.error(f"  ❌ Failed to access repository: {e}")
        return False
    
    # Collect code files
    logger.info(f"\n📂 Scanning repository for code files...")
    docs = []
    
    def process_contents(contents_list, path_prefix=""):
        for content in contents_list:
            try:
                if content.type == "dir":
                    # Skip common non-code directories
                    if content.name in ['.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']:
                        continue
                    # Recursively process directories
                    sub_contents = repo.get_contents(content.path)
                    process_contents(sub_contents, content.path + "/")
                    
                elif content.type == "file":
                    # Only process code files
                    language = detect_language(content.name)
                    if language != 'unknown':
                        try:
                            file_content = content.decoded_content.decode('utf-8')
                            
                            doc = {
                                "file_path": content.path,
                                "content": file_content,
                                "language": language,
                                "repository": f"{GITHUB_OWNER}/{GITHUB_REPO}",
                                "size_bytes": content.size,
                                "last_modified": datetime.utcnow().isoformat(),
                            }
                            docs.append(doc)
                            logger.info(f"    ✓ {content.path} ({language})")
                        except Exception as e:
                            logger.warning(f"    ⚠ Skipped {content.path}: {e}")
            except Exception as e:
                logger.warning(f"    ⚠ Error processing {content.path if hasattr(content, 'path') else 'unknown'}: {e}")
    
    try:
        contents = repo.get_contents("")
        process_contents(contents)
    except Exception as e:
        logger.error(f"  ❌ Failed to scan repository: {e}")
        return False
    
    logger.info(f"\n  Found {len(docs)} code files")
    
    if not docs:
        logger.warning("  ⚠ No code files found")
        return False
    
    # Connect to Elasticsearch
    logger.info(f"\n💾 Connecting to Elasticsearch...")
    try:
        es = Elasticsearch(
            hosts=[ES_URL],
            api_key=ES_API_KEY,
            verify_certs=True
        )
        if not es.ping():
            logger.error("  ❌ Cannot connect to Elasticsearch")
            return False
        logger.info("  ✓ Connected to Elasticsearch")
    except Exception as e:
        logger.error(f"  ❌ Elasticsearch connection failed: {e}")
        return False
    
    # Index documents
    logger.info(f"\n📥 Indexing {len(docs)} files to 'code-repository'...")
    
    actions = [
        {
            "_index": "code-repository",
            "_source": doc
        }
        for doc in docs
    ]
    
    try:
        success, failed = bulk(es, actions, raise_on_error=False)
        logger.info(f"  ✓ Indexed {success} documents")
        if failed:
            logger.warning(f"  ⚠ Failed to index {len(failed)} documents")
    except Exception as e:
        logger.error(f"  ❌ Bulk indexing failed: {e}")
        return False
    
    # Verify
    logger.info(f"\n🔍 Verifying...")
    count = es.count(index="code-repository")['count']
    logger.info(f"  ✓ Total documents in code-repository: {count}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ Code Ingestion Complete!")
    logger.info("="*70)
    logger.info(f"\n🎯 Your agent can now:")
    logger.info(f"   ✓ Search code from {GITHUB_OWNER}/{GITHUB_REPO}")
    logger.info(f"   ✓ Find relevant functions and modules")
    logger.info(f"   ✓ Generate code fixes based on actual code")
    
    logger.info(f"\n💬 Try asking the agent:")
    logger.info(f'   "Show me the authentication code"')
    logger.info(f'   "Find all database connection code"')
    logger.info(f'   "Search for error handling in the API"')
    
    return True


if __name__ == "__main__":
    success = ingest_code()
    sys.exit(0 if success else 1)
