from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="first_name")

    class Meta:
        model = User
        fields = ["id", "email", "name"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        # Django's built-in password rules: length, not too common, not all digits, not like the email.
        user = User(username=attrs["email"], email=attrs["email"], first_name=attrs["name"])
        validate_password(attrs["password"], user)
        return attrs

    def create(self, validated):
        # The email doubles as the username; the password is stored as a salted hash.
        return User.objects.create_user(
            username=validated["email"], email=validated["email"],
            password=validated["password"], first_name=validated["name"],
        )
