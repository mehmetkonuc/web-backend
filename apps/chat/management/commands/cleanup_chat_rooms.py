from django.core.management.base import BaseCommand
from apps.chat.models import ChatRoom

class Command(BaseCommand):
    help = 'Permanently deletes chat rooms where all participants have marked them as deleted'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Count how many chat rooms would be deleted
        rooms_to_delete = []
        
        for chat_room in ChatRoom.objects.all():
            participants = set(chat_room.participants.all().values_list('id', flat=True))
            deleted_by = set(chat_room.deleted_by.all().values_list('id', flat=True))
            
            if participants and participants == deleted_by:
                rooms_to_delete.append(chat_room.id)
        
        count = len(rooms_to_delete)
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No chat rooms to delete.'))
            return
            
        # Ask for confirmation unless --force is specified
        if not options['force']:
            confirm = input(f'\nYou are about to permanently delete {count} chat rooms and all their messages. This action cannot be undone.\n'
                           f'Do you want to continue? [y/N]: ')
            
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return
        
        # Perform the deletion
        deleted_count = ChatRoom.cleanup_deleted_rooms()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} chat rooms and their messages.')) 