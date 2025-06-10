from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from apps.profiles.models import Profile
from apps.dataset.models import University, Department, GraduationStatus
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import uuid
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    """Mevcut kullanıcı bilgilerini gösteren serializer."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active']


class ProfileSerializer(serializers.ModelSerializer):
    """Kullanıcı profil bilgilerini gösteren serializer."""
    university_name = serializers.CharField(source='university.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    graduation_status_name = serializers.CharField(source='graduation_status.name', read_only=True)
    
    class Meta:
        model = Profile
        fields = ['university', 'university_name', 'department', 'department_name', 
                 'graduation_status', 'graduation_status_name', 'is_verified']


class UserWithProfileSerializer(serializers.ModelSerializer):
    """Kullanıcı ve profil bilgilerini birlikte gösteren serializer."""
    profile = ProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active', 'profile']


class Step1RegisterSerializer(serializers.ModelSerializer):
    """İki adımlı kayıt sürecinin ilk adımı için serializer."""
    
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    
    password2 = serializers.CharField(
        write_only=True, 
        required=True
    )
    
    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Şifreler eşleşmiyor"}
            )
        return attrs


class Step2RegisterSerializer(serializers.Serializer):
    """İki adımlı kayıt sürecinin ikinci adımı için serializer."""
    
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    password = serializers.CharField(read_only=True)
    
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=True
    )
    graduation_status = serializers.PrimaryKeyRelatedField(
        queryset=GraduationStatus.objects.all(),
        required=True    )
    
    def create(self, validated_data):
        step1_data = self.context.get('step1_data', {})
        if not step1_data:
            raise serializers.ValidationError("İlk adım verileri eksik")
        
        # Kullanıcı oluştur
        user = User.objects.create(
            username=step1_data['username'],
            email=step1_data['email'],
            first_name=step1_data['first_name'],
            last_name=step1_data['last_name']
        )
        user.set_password(step1_data['password'])
        user.save()
        
        # E-posta adresinin edu.tr ile bitip bitmediğini kontrol et
        email = step1_data['email'].lower()
        is_edu_email = email.endswith('.edu.tr')
        
        # Doğrulama kodu oluştur
        import uuid
        from django.utils import timezone
        verification_token = uuid.uuid4()
        
        # Profil oluştur
        profile = Profile.objects.create(
            user=user,
            university=validated_data['university'],
            department=validated_data['department'],
            graduation_status=validated_data['graduation_status'],
            is_verified=False,  # E-posta doğrulandıktan sonra ve edu.tr ise True olacak
            email_verified=False,
            email_verification_token=verification_token,
            email_verification_sent_at=timezone.now()
        )
        
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """Tek adımlı kayıt için serializer (geriye dönük uyumluluk)."""
    
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    
    password2 = serializers.CharField(
        write_only=True, 
        required=True
    )
    
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=True,
        write_only=True
    )
    
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=True,
        write_only=True
    )
    
    graduation_status = serializers.PrimaryKeyRelatedField(
        queryset=GraduationStatus.objects.all(),
        required=True,
        write_only=True
    )
    
    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name',
                 'university', 'department', 'graduation_status')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Şifreler eşleşmiyor"}
            )
        return attrs
    
    def create(self, validated_data):
        university = validated_data.pop('university')
        department = validated_data.pop('department')
        graduation_status = validated_data.pop('graduation_status')
        validated_data.pop('password2')
        
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        
        # E-posta adresinin edu.tr ile bitip bitmediğini kontrol et
        email = validated_data['email'].lower()
        is_edu_email = email.endswith('.edu.tr')
        
        # Profil oluştur
        Profile.objects.create(
            user=user,
            university=university,
            department=department,
            graduation_status=graduation_status,
            is_verified=is_edu_email
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Email veya kullanıcı adı ile giriş için serializer."""
    
    login_identifier = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    remember_me = serializers.BooleanField(default=False, required=False)


class ChangePasswordSerializer(serializers.Serializer):
    """Şifre değişikliği için serializer."""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Şifreler eşleşmiyor"}
            )
        return attrs


class UsernameCheckSerializer(serializers.Serializer):
    """Kullanıcı adının kullanılabilirliğini kontrol eden serializer."""
    username = serializers.CharField(required=True)
    
    def validate_username(self, value):
        """Kullanıcı adı geçerli mi kontrol et."""
        if len(value) < 3:
            raise serializers.ValidationError("Kullanıcı adı en az 3 karakter olmalıdır.")
        return value


class PasswordResetStep1Serializer(serializers.Serializer):
    """Şifre sıfırlamanın ilk adımı: Email veya kullanıcı adı alınır."""
    identifier_type = serializers.ChoiceField(choices=['email', 'username'], required=True)
    identifier = serializers.CharField(required=True)
    
    def validate(self, attrs):
        identifier_type = attrs.get('identifier_type')
        identifier = attrs.get('identifier')
        
        if identifier_type == 'email':
            # E-posta formatı doğrulama
            try:
                validate_email(identifier)
            except ValidationError:
                raise serializers.ValidationError({"identifier": "Geçerli bir e-posta adresi giriniz."})
            
            # E-posta adresinin sistemde kayıtlı olup olmadığını kontrol et
            if not User.objects.filter(email__iexact=identifier).exists():
                raise serializers.ValidationError({"identifier": "Bu e-posta adresine sahip bir kullanıcı bulunamadı."})
        
        elif identifier_type == 'username':
            # Kullanıcı adının sistemde kayıtlı olup olmadığını kontrol et
            if not User.objects.filter(username__iexact=identifier).exists():
                raise serializers.ValidationError({"identifier": "Bu kullanıcı adına sahip bir kullanıcı bulunamadı."})
        
        return attrs


class PasswordResetStep2Serializer(serializers.Serializer):
    """Şifre sıfırlamanın ikinci adımı: İlk adımda girilen bilgiye göre diğer bilgi alınır."""
    identifier_type = serializers.ChoiceField(choices=['email', 'username'], read_only=True)
    identifier = serializers.CharField(read_only=True)
    verification_value = serializers.CharField(required=True)
    
    def validate(self, attrs):
        # Context'ten ilk adımda girilen bilgileri al
        step1_data = self.context.get('step1_data', {})
        if not step1_data:
            raise serializers.ValidationError("İlk adım verileri eksik.")
            
        identifier_type = step1_data.get('identifier_type')
        identifier = step1_data.get('identifier')
        verification_value = attrs.get('verification_value')
        
        # İlk adımda email girilmişse kullanıcı adını doğrula
        if identifier_type == 'email':
            user = User.objects.filter(email__iexact=identifier).first()
            if not user or user.username.lower() != verification_value.lower():
                raise serializers.ValidationError({"verification_value": "Girilen kullanıcı adı, e-posta adresine ait değil."})
        
        # İlk adımda kullanıcı adı girilmişse email'i doğrula
        elif identifier_type == 'username':
            user = User.objects.filter(username__iexact=identifier).first()
            if not user or user.email.lower() != verification_value.lower():
                raise serializers.ValidationError({"verification_value": "Girilen e-posta adresi, kullanıcı adına ait değil."})
        
        # Doğrulanan kullanıcıyı context'e ekle
        self.context['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Şifre sıfırlama token'ı ve yeni şifre doğrulama."""
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True, 
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Şifreler eşleşmiyor."})
        return attrs