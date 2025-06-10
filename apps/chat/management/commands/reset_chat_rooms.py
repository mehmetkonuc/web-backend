from django.core.management.base import BaseCommand
from apps.chat.models import ChatRoom

class Command(BaseCommand):
    help = 'Sohbet odalarını sıfırlar: mesajı olan odaları aktif yapar, olmayanları devre dışı bırakır'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Sohbet odalarının durumu güncelleniyor...'))
        
        # Tüm sohbet odalarını al
        chat_rooms = ChatRoom.objects.all()
        self.stdout.write(f'Toplam {chat_rooms.count()} sohbet odası bulundu')
        
        active_count = 0
        inactive_count = 0
        
        for chat_room in chat_rooms:
            # Eğer sohbet odasında mesaj varsa, aktif olarak işaretle
            has_messages = chat_room.messages.exists()
            
            if has_messages:
                chat_room.is_active = True
                active_count += 1
            else:
                chat_room.is_active = False
                inactive_count += 1
                
            chat_room.save(update_fields=['is_active'])
        
        self.stdout.write(self.style.SUCCESS(f'İşlem tamamlandı. {active_count} sohbet odası aktif, {inactive_count} sohbet odası devre dışı olarak işaretlendi.')) 