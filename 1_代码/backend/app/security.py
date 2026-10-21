import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pwdlib import PasswordHash
from app.errors import require, BusinessError

passwords = PasswordHash.recommended()


def now():
    value = datetime.now(timezone.utc)
    # BSON 精度为毫秒；首次响应与幂等重试采用一致精度。
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


def uid():
    return secrets.token_hex(12)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Security:
    def __init__(self, secret):
        require(
            len(secret) >= 32 and not secret.startswith("replace-"),
            "请先设置至少 32 字符的随机 SECRET_KEY",
            500,
        )
        self.secret = secret
        self.signer = URLSafeTimedSerializer(secret, salt="survey-attempt-v1")

    def respondent_key(self, survey_id, user_id):
        return hmac.new(
            self.secret.encode(), f"{survey_id}:{user_id}".encode(), hashlib.sha256
        ).hexdigest()

    def issue(self, survey, version, user, anonymous):
        return self.signer.dumps(
            {
                "survey_id": survey["_id"],
                "version_id": version["_id"],
                "user_id": user["_id"],
                "anonymous": anonymous,
                "attempt_id": uid(),
            }
        )

    def decode(self, token):
        try:
            return self.signer.loads(token, max_age=86400)
        except (BadSignature, SignatureExpired):
            raise BusinessError("填写凭证无效或已过期，请重新进入问卷", 401)


def new_session(db, user_id):
    token = secrets.token_urlsafe(32)
    db.sessions.insert_one(
        {
            "_id": uid(),
            "token_hash": digest(token),
            "user_id": user_id,
            "expires_at": now() + timedelta(days=7),
        }
    )
    return token
