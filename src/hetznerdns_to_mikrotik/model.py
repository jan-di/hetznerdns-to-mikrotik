"""
Data models for DNS records.
"""


class Record:
    """
    Represents a DNS record.
    """

    def __init__(self, record_type, name, ttl, value=None):
        self.record_type = record_type
        self.name = name
        self.value = value
        self.ttl = ttl

    def get_uid(self) -> str:
        """
        Returns a unique identifier for the record based on its name, type, and content.
        """

        return f"{self.name}-{self.record_type}-{self.value}"

    def __str__(self) -> str:
        return f"{self.record_type.rjust(5, ' ')} {self.name} {self.value} {self.ttl if self.ttl else '-'}"
