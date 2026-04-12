from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_page, name='upload'),
    path('compare/', views.compare, name='compare'),
    path('contact/', views.contact, name='contact'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('analyze/', views.analyze_document, name='analyze'),
    path('result/<int:document_id>/', views.result_detail, name='result'),
    path('ask/<int:document_id>/', views.ask_question, name='ask_question'),
    path('compare/papers/<int:doc1_id>/<int:doc2_id>/', views.compare_papers, name='compare_papers'),
    path('library/', views.library, name='library'),
    path('delete/<int:document_id>/', views.delete_document, name='delete'),
    path('export/<int:document_id>/<str:export_format>/', views.export_document, name='export'),
    path('email/<int:document_id>/', views.email_report, name='email_report'),
    path('feedback/<int:document_id>/', views.submit_feedback, name='feedback'),
    path('health/', views.health_check, name='health'),
]
