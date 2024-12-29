class Record():
    def __init__(self, record_type, name, ttl, content = None):
        self.record_type = record_type
        self.name = name
        self.content = content
        self.ttl = ttl

    def get_uid(self):
        return f"{self.name}-{self.record_type}-{self.content}"

    def __str__(self):
        return f"{self.record_type.rjust(5, ' ')} {self.name} {self.content} {self.ttl if self.ttl else '-'}"