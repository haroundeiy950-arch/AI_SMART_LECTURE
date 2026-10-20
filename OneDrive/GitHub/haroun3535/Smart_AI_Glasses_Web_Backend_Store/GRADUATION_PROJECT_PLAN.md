# Graduation Project Plan

## Project Title

**Smart AI Glasses Web Platform for Assistive Vision, Multilingual Communication and Secure Interaction**

## Problem

المستخدم يحتاج إلى نظام يجمع فهم البيئة، قراءة النصوص، الترجمة، المساعدة الصوتية، دعم الاجتماعات والأمان، مع واجهة سهلة تعمل على الكمبيوتر ويمكن لاحقًا ربطها بنظارة فعلية.

## Main Objectives

1. تطوير واجهة ويب موحدة لإدارة جميع وحدات النظارة.
2. توفير وصول آمن بكلمة مرور وWindows Hello.
3. تحليل صور الكاميرا وعرض النتائج في الزمن شبه الحقيقي.
4. تقديم مساعد صوتي متعدد اللغات.
5. دعم الاجتماعات بالتفريغ والتلخيص والمهام.
6. حفظ البيانات بصورة منظمة مع النسخ الاحتياطي والخصوصية.

## Actors

- Administrator
- Normal User
- Registered Person
- Meeting Participant

## Functional Requirements

- Authentication and authorization.
- Passkey registration and authentication.
- Camera permission and frame capture.
- Person registration and face dataset management.
- Scene/object/text analysis.
- Speech-to-text and text-to-speech.
- AI text assistant.
- Multilingual translation.
- Meeting summary and task extraction.
- Security logs and backups.

## Non-functional Requirements

- Security: Argon2, CSRF token, HttpOnly session cookie, login throttling.
- Privacy: explicit camera/microphone permission and controlled capture.
- Usability: responsive browser interface.
- Maintainability: modular Python services.
- Reliability: local fallback for key features.
- Scalability: migration path from SQLite to PostgreSQL.

## Recommended Evaluation

- Login success/failure test.
- Windows Hello registration and login test.
- Camera permission and capture test.
- AI response latency.
- Speech transcription accuracy under noise.
- Object/OCR result accuracy on prepared test scenes.
- Meeting summary quality questionnaire.
- User usability survey.

## Development Phases

1. Core web platform and database.
2. Password authentication and dashboard.
3. Passkeys and Windows Hello.
4. Camera and person registration.
5. AI voice and transcription.
6. Translation, meetings and reports.
7. Local face-recognition engine.
8. Testing, security hardening and documentation.
