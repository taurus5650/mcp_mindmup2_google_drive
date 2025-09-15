import asyncio
import pytest
import pytest_asyncio
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_manager import MindMupManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def gdrive_client():
    """Fixture to provide authenticated Google Drive client."""
    # Load environment variables from project root
    env_path = os.path.join(project_root, 'deployment', '.env.dev')
    load_dotenv(dotenv_path=env_path)

    # Setup credentials
    default_creds = os.path.join(project_root, 'deployment', 'credentials', 'google_service_account.json')
    creds_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', default_creds)

    if not os.path.exists(creds_file) and os.path.exists(default_creds):
        os.environ['GOOGLE_DRIVE_CREDENTIALS_FILE'] = default_creds
        creds_file = default_creds

    client = GoogleDriveClient()

    # Override credentials path from environment
    if creds_file:
        client.config.google_drive.credentials_file = creds_file
        logger.info(f'Using credentials file: {creds_file}')

    # Authenticate
    auth_result = await client.authenticate()
    assert auth_result.success, f'Google Drive authentication failed: {auth_result.error}'

    return client


@pytest_asyncio.fixture
async def mindmup_manager(gdrive_client):
    """Fixture to provide MindMup manager with authenticated client."""
    return MindMupManager(gdrive_client)


@pytest.mark.asyncio
async def test_gdrive_authentication():
    """Test Google Drive authentication."""
    # Load environment variables
    env_path = os.path.join(project_root, 'deployment', '.env.dev')
    load_dotenv(dotenv_path=env_path)

    # Setup credentials
    default_creds = os.path.join(project_root, 'deployment', 'credentials', 'google_service_account.json')
    creds_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', default_creds)

    if not os.path.exists(creds_file) and os.path.exists(default_creds):
        os.environ['GOOGLE_DRIVE_CREDENTIALS_FILE'] = default_creds
        creds_file = default_creds

    client = GoogleDriveClient()

    if creds_file:
        client.config.google_drive.credentials_file = creds_file

    logger.info('Testing Google Drive authentication')
    auth_result = await client.authenticate()

    assert auth_result.success, f'Authentication should succeed: {auth_result.error}'
    logger.info('Google Drive authentication successful')


@pytest.mark.asyncio
async def test_search_mindmup_files_in_folder(mindmup_manager):
    """Test searching for MindMup files in a specific folder."""
    target_folder_id = "196S0FvNOi1_IcYdgi6OnrWw1kMELF4-7"

    logger.info(f'Searching for MindMup files in folder: {target_folder_id}')
    mindmup_files = await mindmup_manager.search_mindmup_files(folder_id=target_folder_id)

    assert isinstance(mindmup_files, list), "Should return a list of files"

    if mindmup_files:
        logger.info(f'Found {len(mindmup_files)} MindMup file(s)')
        for file_info in mindmup_files:
            logger.info(f'MindMup name: {file_info.name}')
            logger.info(f'MindMup ID: {file_info.id}')
            logger.info(f'MindMup type: {file_info.mime_type}')

            assert file_info.name is not None, "File should have a name"
            assert file_info.id is not None, "File should have an ID"
            assert 'mindmup' in file_info.mime_type.lower(), "Should be a MindMup file"

            if file_info.web_view_link:
                logger.info(f'MindMup link: {file_info.web_view_link}')
                assert file_info.web_view_link.startswith('https://'), "Should have valid web link"
    else:
        logger.info('No MindMup files found in specified folder')


@pytest.mark.asyncio
async def test_search_all_mindmup_files(mindmup_manager):
    """Test searching for all MindMup files in Google Drive."""
    logger.info('Searching all Google Drive for MindMup files...')
    all_mindmup_files = await mindmup_manager.search_mindmup_files()

    assert isinstance(all_mindmup_files, list), "Should return a list of files"

    if all_mindmup_files:
        logger.info(f'Found {len(all_mindmup_files)} MindMup file(s) in Google Drive')
        for file_info in all_mindmup_files:
            logger.info(f'{file_info.name} (ID: {file_info.id})')

            assert file_info.name is not None, "File should have a name"
            assert file_info.id is not None, "File should have an ID"
    else:
        logger.info('No MindMup files found in Google Drive')


@pytest.mark.asyncio
async def test_load_mindmup_content(mindmup_manager):
    """Test loading content of a specific MindMup file."""
    # First find a MindMup file
    all_files = await mindmup_manager.search_mindmup_files()

    if all_files:
        test_file = all_files[0]
        logger.info(f'Testing content loading for: {test_file.name} (ID: {test_file.id})')

        result = await mindmup_manager.load_minmdup(file_id=test_file.id)

        assert hasattr(result, 'success'), "Result should have success attribute"
        if result.success:
            assert result.data is not None, "Should return mindmap data"
            logger.info(f'Successfully loaded mindmap content')
        else:
            logger.warning(f'Failed to load mindmap: {result.error}')
    else:
        pytest.skip("No MindMup files available for content testing")


@pytest.mark.asyncio
async def test_list_accessible_folders(mindmup_manager):
    """Test listing accessible folders in Google Drive."""
    logger.info('Testing folder listing...')
    folders = await mindmup_manager.list_accessible_folders()

    assert isinstance(folders, list), "Should return a list of folders"

    if folders:
        logger.info(f'Found {len(folders)} accessible folder(s)')
        for folder in folders[:5]:  # Log first 5 folders
            logger.info(f'Folder: {folder.name} (ID: {folder.id})')

            assert folder.name is not None, "Folder should have a name"
            assert folder.id is not None, "Folder should have an ID"
    else:
        logger.info('No accessible folders found')


if __name__ == '__main__':
    # Allow running individual tests directly
    pytest.main([__file__, '-v'])