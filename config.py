import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SUPABASE_URL = os.environ.get('SUPABASE_URL') or 'https://your-default-url.supabase.co'
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY') or 'your-default-supabase-key'
    ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'sample@email.com').split(',')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')