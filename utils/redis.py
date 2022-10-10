import redis

from django.conf import settings


class Redis:
    def __init__(self):
        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.client = redis.Redis(host=self.host, port=self.port)

    def setkey(self, key, value):
        return self.client.set(key, value)

    def getkey(self, key):
        return self.client.get(key)

    def delkey(self, key):
        return self.client.delete(key)
