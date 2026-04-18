from django.contrib.auth import get_user_model
from django.db import models

from apps.models import SavingsGroup
User = get_user_model()
POST_TYPES = [
    ("post", "Post"),
    ("message", "Message"),
    ("comment", "Comment"),
]


class Post(models.Model):
    """Group post/message imported from WhatsApp"""

    group = models.ForeignKey(SavingsGroup, on_delete=models.CASCADE, related_name="posts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts", null=True, blank=True)
    sender = models.CharField(max_length=100)
    content = models.TextField()
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default="message")
    timestamp = models.DateTimeField()
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    raw_members = models.JSONField(default=list)
    raw_line = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.sender}: {self.post_type} on {self.timestamp.date()}"
