"""
Advanced Image Processing Utility for Django Backend
Mobil taraftan gelen sıkıştırılmış resimleri daha da optimize eder.

Bu utility şunları yapar:
- WebP formatına çevirme (daha küçük dosya boyutu)
- Multiple sizes oluşturma (thumbnail, medium, large)
- Quality optimization
- Metadata cleaning (EXIF data removal)
- Hash-based duplicate detection
- Progressive JPEG optimization
"""

import os
import hashlib
import logging
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image, ImageOps, ExifTags
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

# python-magic yerine mimetypes kullanılacak (daha güvenli)
import mimetypes

# Logging setup
logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Advanced image processing for Django backend.
    Mobil taraftan gelen resimleri daha da optimize eder.
    """
    
    # Desteklenen format mappings
    SUPPORTED_INPUT_FORMATS = {
        'JPEG': 'image/jpeg',
        'JPG': 'image/jpeg', 
        'PNG': 'image/png',
        'WEBP': 'image/webp',
        'BMP': 'image/bmp',
        'TIFF': 'image/tiff'
    }
    
    # Çıktı format ayarları
    OUTPUT_FORMAT = 'WEBP'  # En optimize format
    FALLBACK_FORMAT = 'JPEG'  # Eski browser desteği için
    
    # Boyut presetleri (farklı kullanım alanları için)
    SIZE_PRESETS = {
        'thumbnail': (150, 150),      # Avatar thumbnails
        'small': (300, 300),          # List view images
        'medium': (600, 600),         # Detail view images  
        'large': (1200, 1200),        # Full size view
        'original': None              # Orijinal boyut (sınırlı)
    }
    
    # Kalite ayarları
    QUALITY_SETTINGS = {
        'thumbnail': 75,   # Küçük resimler için daha düşük kalite
        'small': 80,       # 
        'medium': 85,      # Orta boyut için iyi kalite
        'large': 90,       # Büyük resimler için yüksek kalite
        'original': 95     # Orijinal için en yüksek kalite
    }
    
    # Maksimum dosya boyutları (bytes)
    MAX_FILE_SIZES = {
        'thumbnail': 50 * 1024,      # 50KB
        'small': 150 * 1024,         # 150KB
        'medium': 300 * 1024,        # 300KB
        'large': 800 * 1024,         # 800KB
        'original': 2 * 1024 * 1024  # 2MB
    }

    def __init__(self):
        """Image processor'ı başlat"""
        # WebP desteği kontrolü
        self.webp_supported = self._check_webp_support()
        if not self.webp_supported:
            logger.warning("WebP desteği bulunamadı, JPEG fallback kullanılacak")
    
    def _check_webp_support(self) -> bool:
        """WebP desteği var mı kontrol et"""
        try:
            # Test WebP image oluştur
            test_image = Image.new('RGB', (1, 1), color='white')
            buffer = BytesIO()
            test_image.save(buffer, format='WEBP')
            return True
        except Exception as e:
            logger.error(f"WebP desteği kontrolü başarısız: {e}")
            return False
    
    def _get_image_hash(self, image_data: bytes) -> str:
        """Resmin hash'ini hesapla (duplicate detection için)"""
        return hashlib.md5(image_data).hexdigest()
    
    def _clean_metadata(self, image: Image.Image) -> Image.Image:
        """EXIF metadata'yı temizle (privacy ve boyut için)"""
        try:
            # EXIF verilerini temizle
            cleaned_image = Image.new(image.mode, image.size)
            cleaned_image.putdata(list(image.getdata()))
            return cleaned_image
        except Exception as e:
            logger.warning(f"Metadata temizleme hatası: {e}")
            return image
    
    def _optimize_orientation(self, image: Image.Image) -> Image.Image:
        """Resim orientation'ını düzelt (EXIF based rotation)"""
        try:
            return ImageOps.exif_transpose(image)
        except Exception as e:
            logger.warning(f"Orientation düzeltme hatası: {e}")
            return image
    
    def _resize_image(self, image: Image.Image, size_preset: str) -> Image.Image:
        """Resmi belirtilen preset'e göre yeniden boyutlandır"""
        if size_preset == 'original':
            # Orijinal boyut için sadece max limit uygula
            max_dimension = 2048  # 2K maksimum
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            return image
        
        target_size = self.SIZE_PRESETS.get(size_preset)
        if not target_size:
            raise ValueError(f"Geçersiz size preset: {size_preset}")
        
        # Aspect ratio'yu koru
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        return image
    
    def _convert_to_format(self, image: Image.Image, format_type: str, quality: int) -> BytesIO:
        """Resmi belirtilen formata çevir"""
        buffer = BytesIO()
        
        # RGB'ye çevir (WEBP ve JPEG için gerekli)
        if image.mode in ('RGBA', 'P'):
            # Transparent background'u beyaz yap
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Format'a göre kaydet
        if format_type == 'WEBP' and self.webp_supported:
            image.save(buffer, format='WEBP', quality=quality, optimize=True)
        else:
            # JPEG fallback
            image.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
        
        buffer.seek(0)
        return buffer
    
    def process_image(self, 
                     image_file, 
                     size_presets: Optional[List[str]] = None,
                     context: str = 'general') -> Dict[str, Dict]:
        """
        Ana resim işleme fonksiyonu
        
        Args:
            image_file: Django UploadedFile objesi
            size_presets: İşlenecek boyut presetleri ['thumbnail', 'medium', 'large']
            context: Kullanım konteksti ('profile', 'post', 'chat', 'comment')
            
        Returns:
            Dict: Her preset için işlenmiş resim bilgileri
        """
        if size_presets is None:
            # Context'e göre default presetler
            context_presets = {
                'profile': ['thumbnail', 'medium'],
                'post': ['thumbnail', 'medium', 'large'],
                'chat': ['thumbnail', 'medium'],
                'comment': ['thumbnail', 'small']
            }
            size_presets = context_presets.get(context, ['thumbnail', 'medium'])
        
        try:
            # Orijinal resmi yükle
            original_image = Image.open(image_file)
            logger.info(f"Resim işleniyor: {image_file.name}, boyut: {original_image.size}, format: {original_image.format}")
            
            # Orientation'ı düzelt
            original_image = self._optimize_orientation(original_image)
            
            # Metadata'yı temizle
            original_image = self._clean_metadata(original_image)
            
            # Hash hesapla (duplicate detection için)
            image_file.seek(0)
            image_hash = self._get_image_hash(image_file.read())
            
            results = {}
            
            # Her preset için işle
            for preset in size_presets:
                try:
                    # Resmi yeniden boyutlandır
                    processed_image = self._resize_image(original_image.copy(), preset)
                    
                    # Kalite ayarını al
                    quality = self.QUALITY_SETTINGS.get(preset, 85)
                    
                    # Format'a çevir
                    format_type = self.OUTPUT_FORMAT if self.webp_supported else self.FALLBACK_FORMAT
                    image_buffer = self._convert_to_format(processed_image, format_type, quality)
                    
                    # Dosya boyutunu kontrol et
                    max_size = self.MAX_FILE_SIZES.get(preset, 500 * 1024)
                    if image_buffer.getbuffer().nbytes > max_size:
                        # Kaliteyi düşür ve tekrar dene
                        for reduced_quality in [quality - 10, quality - 20, quality - 30]:
                            if reduced_quality < 30:
                                break
                            image_buffer = self._convert_to_format(processed_image, format_type, reduced_quality)
                            if image_buffer.getbuffer().nbytes <= max_size:
                                break
                    
                    # Dosya extension'ını belirle
                    extension = '.webp' if format_type == 'WEBP' else '.jpg'
                    
                    results[preset] = {
                        'image_data': image_buffer,
                        'size': processed_image.size,
                        'file_size': image_buffer.getbuffer().nbytes,
                        'format': format_type,
                        'quality': quality,
                        'extension': extension,
                        'hash': image_hash
                    }
                    
                    logger.info(f"Preset '{preset}' işlendi: {processed_image.size}, {image_buffer.getbuffer().nbytes} bytes")
                    
                except Exception as e:
                    logger.error(f"Preset '{preset}' işlenirken hata: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Resim işleme hatası: {e}")
            raise ValueError(f"Resim işlenemedi: {str(e)}")
    
    def save_processed_images(self, 
                            processed_images: Dict[str, Dict],
                            base_filename: str,
                            upload_path: str = 'processed/') -> Dict[str, str]:
        """
        İşlenmiş resimleri storage'a kaydet
        
        Args:
            processed_images: process_image'dan dönen sonuçlar
            base_filename: Temel dosya adı
            upload_path: Upload klasör yolu
            
        Returns:
            Dict: Her preset için dosya yolları
        """
        saved_files = {}
        
        # Güvenli dosya adı oluştur
        safe_filename = os.path.splitext(base_filename)[0]
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        for preset, image_data in processed_images.items():
            try:
                # Dosya adını oluştur
                filename = f"{safe_filename}_{preset}{image_data['extension']}"
                file_path = os.path.join(upload_path, filename)
                
                # ContentFile oluştur
                content_file = ContentFile(image_data['image_data'].getvalue())
                
                # Storage'a kaydet
                saved_path = default_storage.save(file_path, content_file)
                saved_files[preset] = saved_path
                
                logger.info(f"Resim kaydedildi: {saved_path}")
                
            except Exception as e:
                logger.error(f"Resim kaydetme hatası ({preset}): {e}")
                continue
        
        return saved_files
    
    def get_image_info(self, image_file) -> Dict:
        """Resim hakkında bilgi al (validation için)"""
        try:
            # MIME type kontrolü
            mime_type = mimetypes.guess_type(image_file.name)[0]
            if not mime_type:
                # Fallback: dosya başlığından tespit et
                image_file.seek(0)
                header = image_file.read(8)
                image_file.seek(0)
                
                if header.startswith(b'\xFF\xD8\xFF'):
                    mime_type = 'image/jpeg'
                elif header.startswith(b'\x89PNG'):
                    mime_type = 'image/png'
                elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/unknown'
            
            # PIL ile resmi aç
            image = Image.open(image_file)
            
            return {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'mime_type': mime_type,
                'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            }
            
        except Exception as e:
            logger.error(f"Resim bilgisi alınamadı: {e}")
            raise ValueError(f"Geçersiz resim dosyası: {str(e)}")


# Convenience functions
def process_profile_image(image_file, user_id: Optional[int] = None):
    """Profil resmi için optimize edilmiş işleme"""
    processor = ImageProcessor()
    processed = processor.process_image(
        image_file, 
        size_presets=['thumbnail', 'medium'],
        context='profile'
    )
    
    # Date-based path structure: avatars/2025/07/15/100/
    from datetime import datetime
    now = datetime.now()
    upload_path = f'avatars/{now.year}/{now.month:02d}/{now.day:02d}/{user_id}/' if user_id else f'avatars/{now.year}/{now.month:02d}/{now.day:02d}/temp/'
    
    # Clean filename için sadece user_id kullan
    import uuid
    clean_name = f"user_{user_id}_{str(uuid.uuid4())[:8]}"
    return processor.save_processed_images(processed, clean_name, upload_path)

def process_post_images(image_files: List, post_id: Optional[int] = None):
    """Post resimleri için optimize edilmiş işleme"""
    processor = ImageProcessor()
    results = []
    
    for i, image_file in enumerate(image_files):
        processed = processor.process_image(
            image_file,
            size_presets=['thumbnail', 'medium', 'large'],
            context='post'
        )
        
        # Create date-based upload path with post ID folder (same as model)
        from datetime import datetime
        now = datetime.now()
        upload_path = f'posts/{now.year}/{now.month:02d}/{now.day:02d}/{post_id}/'
        saved_files = processor.save_processed_images(processed, f"post_{post_id}_{image_file.name}_{i}", upload_path)
        results.append(saved_files)
    
    return results

def process_chat_image(image_file, chat_id: Optional[int] = None):
    """Chat resmi için optimize edilmiş işleme"""
    processor = ImageProcessor()
    processed = processor.process_image(
        image_file,
        size_presets=['thumbnail', 'medium'],
        context='chat'
    )
    
    # Date-based path structure: chat/2025/07/15/100/
    from datetime import datetime
    now = datetime.now()
    upload_path = f'chat/{now.year}/{now.month:02d}/{now.day:02d}/{chat_id}/' if chat_id else f'chat/{now.year}/{now.month:02d}/{now.day:02d}/temp/'
    return processor.save_processed_images(processed, f"chat_{chat_id}_{image_file.name}", upload_path)

def process_comment_image(image_file, comment_id: Optional[int] = None):
    """Yorum resmi için optimize edilmiş işleme"""
    processor = ImageProcessor()
    processed = processor.process_image(
        image_file,
        size_presets=['thumbnail', 'small'],
        context='comment'
    )
    
    # Date-based path structure: comments/2025/07/15/100/
    from datetime import datetime
    now = datetime.now()
    upload_path = f'comments/{now.year}/{now.month:02d}/{now.day:02d}/{comment_id}/' if comment_id else f'comments/{now.year}/{now.month:02d}/{now.day:02d}/temp/'
    return processor.save_processed_images(processed, f"comment_{comment_id}_{image_file.name}", upload_path)
