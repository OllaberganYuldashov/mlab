"""ADM-02: audit jurnali DB darajasida faqat qo'shiladi (UPDATE va DELETE trigger bilan rad etiladi).

TRUNCATE ataylab bloklanmaydi: pytest-django transactional testlari jadvallarni TRUNCATE bilan tozalaydi.
Kelajakda saqlash muddati tugagan yozuvlarni o'chirish (SRS 7-bo'lim) egasining qarori bilan alohida
migratsiyada hal qilinadi. Orqaga qaytarish: trigger va funksiya o'chiriladi.
"""

from django.db import migrations

FORWARD = """
CREATE FUNCTION audit_auditlog_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_auditlog is append-only (% rejected)', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER audit_auditlog_append_only
BEFORE UPDATE OR DELETE ON audit_auditlog
FOR EACH ROW EXECUTE FUNCTION audit_auditlog_append_only();
"""

REVERSE = """
DROP TRIGGER IF EXISTS audit_auditlog_append_only ON audit_auditlog;
DROP FUNCTION IF EXISTS audit_auditlog_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
