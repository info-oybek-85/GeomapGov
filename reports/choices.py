from django.db import models

class ReportStatus(models.TextChoices):
    NEW = "new", "Yangi"  # foydalanuvchi yubordi
    SENT = "sent", "Tashkilotga yuborildi"  # org ga biriktirildi
    READ = "read", "Tashkilot tomonidan o‘qildi"  # organization ochdi
    ACCEPTED = "accepted", "Qabul qilindi"  # bizniki deb oldi
    ASSIGNED = "assigned", "Xodimga biriktirildi"  # ichida kimdirga yuklandi
    IN_PROGRESS = "in_progress", "Jarayonda"
    PENDING_CONFIRMATION = "pending_confirmation", "Fuqaro tasdig‘i kutilmoqda"
    RESOLVED = "resolved", "Hal qilindi"
    REOPENED = "reopened", "Qayta ishga yuborildi"
    REJECTED = "rejected", "Rad etildi"
    REDIRECTED = "redirected", "Boshqa tashkilotga yo‘naltirildi"



class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    VOICE = "voice", "Voice"
    FILE = "file", "File"
