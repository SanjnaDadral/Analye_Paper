from django.contrib import admin
from .models import Document, AnalysisResult, PlagiarismCheck, ContactMessage, ComparisonResult


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'input_type', 'word_count', 'created_at']
    list_filter = ['input_type', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['document', 'publication_year', 'created_at']
    list_filter = ['publication_year', 'created_at']
    search_fields = ['document__title', 'keywords', 'methodology']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PlagiarismCheck)
class PlagiarismCheckAdmin(admin.ModelAdmin):
    list_display = ['document', 'similarity_score', 'checked_at']
    list_filter = ['checked_at']
    readonly_fields = ['checked_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'email', 'name']
    fieldsets = (
        ('Message Info', {
            'fields': ('name', 'email', 'subject', 'created_at')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
    )
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} message(s) marked as read.")
    mark_as_read.short_description = "Mark selected messages as read"
    
    actions = ['mark_as_read']


@admin.register(ComparisonResult)
class ComparisonResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'document1', 'document2', 'similarity_score', 'created_at']
    list_filter = ['created_at', 'similarity_score']
    search_fields = ['user__username', 'document1__title', 'document2__title']
    readonly_fields = ['created_at', 'similarity_score']
    fieldsets = (
        ('Comparison Info', {
            'fields': ('user', 'document1', 'document2', 'created_at')
        }),
        ('Results', {
            'fields': ('similarity_score', 'comparison_data')
        }),
    )
