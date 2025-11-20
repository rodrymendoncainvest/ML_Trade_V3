from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_port: int = 8000
    mongo_uri: str = "mongodb://mongo:27017"
    redis_url: str = "redis://redis:6379/0"
    broker_url: str = "amqp://guest:guest@rabbitmq:5672//"
    result_backend: str = "redis://redis:6379/1"

    class Config:
        env_file = ".env"

settings = Settings()
