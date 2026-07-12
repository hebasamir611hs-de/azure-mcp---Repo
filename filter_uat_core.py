# -*- coding: utf-8 -*-
"""
Curate the full UAT case set down to the IMPORTANT + DIRECT UAT cases — the core
happy-path acceptance flow(s) per backlog item. Drops QA-level variants
(field-validation negatives, empty-state/error messages, permission-gating,
secondary filter combinations, micro-toggles, sub-flows).

Reads all_cases.json, keeps only the selected indices per PBI, writes
all_cases_core.json (same PBI order; non-UAT PBIs keep their note + empty cases).
"""
import json

SRC = "/Users/asmaa/CI-CD-AI-AU/azure-mcp---Repo/outputs/UAT/_cases/all_cases.json"
OUT = "/Users/asmaa/CI-CD-AI-AU/azure-mcp---Repo/outputs/UAT/_cases/all_cases_core.json"

# kept case indices per PBI (0-based, into the full all_cases.json cases array)
SELECT = {
    123679: [0],          # عرض شاشة البداية
    123680: [3, 4],       # تفعيل الدخول البيومتري + الدخول به بنجاح
    123681: [0],          # تسجيل الخروج عند انتهاء الجلسة
    123684: [2, 3],       # منع الإصدار القديم + السماح للإصدار الحديث
    125308: [1, 3],       # عرض السباقات الافتراضي + الفلترة
    125309: [1, 2],       # عرض مجموعات الأشواط + الفلترة
    125310: [1],          # عرض الأشواط التابعة للمجموعة
    125311: [0, 4],       # تفاصيل الشوط والتبويبات + تبويبة النتائج
    125312: [0, 1],       # عرض الهجن وحالاتها + البحث/الفلترة
    125313: [0, 3],       # تفاصيل المطية + إظهار/إخفاء للعامة
    125314: [0],          # إرسال طلب إصدار بطاقة بنجاح
    125315: [0],          # إرسال طلب تعديل المعلومات بنجاح
    125364: [3, 4],       # إرسال طلب الحذف + منعه عند طلب نقل ملكية
    125366: [0, 1],       # قائمة المضمرين + صفحة التفاصيل وتبويباتها
    125369: [0, 3],       # التوجيه حسب السباقات المفتوحة + المطايا القابلة للتسجيل
    125370: [2, 3],       # إتمام التسجيل + إدارة تسجيل المطية
    125371: [1, 3],       # عرض بيانات الملف الشخصي + تعديل التواصل
    125373: [0, 1],       # عرض الإنجازات + بياناتها وترتيبها
    125374: [0, 2],       # عرض المخالفات + الفلترة
    125376: [0],          # الوصول إلى الإعدادات
    125377: [0],          # عرض محتوى اللجنة
    125379: [1],          # تغيير كلمة المرور بنجاح
    125380: [1, 2],       # تفعيل/إلغاء الدخول بالبصمة
    125381: [1],          # تنفيذ حذف الحساب بعد التأكيد
    125387: [1],          # إرسال طلب إصدار بطاقة مشارك بنجاح
    126697: [0, 2],       # ترويسة الصفحة الرئيسية + الخدمات السريعة
    127322: [0, 2],       # تسجيل الدخول الناجح + رسالة الخطأ
    128936: [0, 1],       # إظهار/إخفاء خيار حذف الحساب
    129268: [0],          # نقل زر تسجيل الخروج إلى المزيد
    129269: [1],          # إرسال كلمة المرور الجديدة بنجاح
    129278: [0, 2],       # رفع الشعار + تعديل صورة المالك
}


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    out, kept, dropped = [], 0, 0
    for entry in data:
        pbi = entry["pbi"]
        cases = entry.get("cases", [])
        if pbi in SELECT and cases:
            idxs = SELECT[pbi]
            new_cases = [cases[i] for i in idxs]
            dropped += len(cases) - len(new_cases)
            kept += len(new_cases)
            out.append({"pbi": pbi, "note": entry.get("note", ""), "cases": new_cases})
        else:
            out.append(entry)  # non-UAT PBIs unchanged (empty + note)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Kept {kept} cases, dropped {dropped}. Wrote {OUT}")


if __name__ == "__main__":
    main()
