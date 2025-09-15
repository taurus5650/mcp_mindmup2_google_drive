import asyncio
import sys
from dotenv import load_dotenv
from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_manager import MindMupManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    try:
        load_dotenv(dotenv_path='deployment/.env')

        gdrive_client = GoogleDriveClient()
        mindmup_manager = MindMupManager(gdrive_client)

        logger.info('Google Drive authentication')
        auth_result = await gdrive_client.authenticate()
        if not auth_result.success:
            return (f'Google Drive authentication failed: {auth_result.error}')

        logger.info('Google Drive authentication successful')

        target_folder_id = "196S0FvNOi1_IcYdgi6OnrWw1kMELF4-7"

        mindmup_files = await mindmup_manager.search_mindmup_files(folder_id=target_folder_id)

        if mindmup_files:
            logger.info(f'Found Mindmup file: {len(mindmup_files)} ')
            for file_info in mindmup_files:
                logger.info(f'Mindmup name: {file_info.name}')
                logger.info(f'Mindmup Id: {file_info.id}')
                logger.info(f'Mindmup type: {file_info.mime_type}')
                if file_info.web_view_link:
                    logger.info(f'Mindmup link: {file_info.web_view_link}')
        else:
            logger.info(f'Mindmup not found')

            logger.info(f'Searching all Google Drive ...')
            all_mindmup_files = await mindmup_manager.search_mindmup_files()

            if all_mindmup_files:
                logger.info(f'Google Drive found Mindmup file: {len(all_mindmup_files)}')
                for file_info in all_mindmup_files:
                    logger.info(f'{file_info.name} (ID: {file_info.id})')
            else:
                logger.info(f'Google Drive not found Mindmup file: {len(all_mindmup_files)}')

    except Exception as e:
        print(f'error: {e}', file=sys.stderr)


if __name__ == '__main__':
    asyncio.run(main())
