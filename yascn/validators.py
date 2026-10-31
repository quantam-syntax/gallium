from django.core.exceptions import ValidationError


def validate_password(value):
    if (len(value) <= 8 or not any(c.isupper() for c in value)
            or not any(c.islower() for c in value)
            or not any(not c.isalnum() and not c.isspace() for c in value)):
        raise ValidationError(
            "Use more than eight characters with uppercase, lowercase, and a special character."
        )
