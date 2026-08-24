# APRAS — Feature Domains Planning & Open Questions Document

**Document Version:** 1.0.0  
**Date:** 2026-08-23  
**Author:** Meridian PM (Task Pipeline Orchestrator)  
**Target Application:** APRAS (*Aplicativo de Planejamento e Resoluções para Associações e Síndicos*)  

---

## Executive Summary

This document provides a comprehensive architectural planning pass, database schema definitions, API/frontend integration mappings, open operational questions, and COM21 competitive benchmarking for 12 new feature domains requested for APRAS.

The corresponding structured Meridian tasks have been registered in `.meridian/tasks.json` (`T001` through `T012`) to drive specs, development, and QA validation through the Meridian pipeline.

---

## Table of Contents

1. [T001: Cadastro de Lotes e Vinculação de Usuários](#1-t001-cadastro-de-lotes-e-vinculação-de-usuários)
2. [T002: Cadastro de Moradores por Lote](#2-t002-cadastro-de-moradores-por-lote)
3. [T003: Cadastro de Visitantes e Prestadores de Serviço](#3-t003-cadastro-de-visitantes-e-prestadores-de-serviço)
4. [T004: Fotos em Cadastros](#4-t004-fotos-em-cadastros)
5. [T005: Controle de Acesso & Reconhecimento Facial](#5-t005-controle-de-acesso--reconhecimento-facial)
6. [T006: Blog/Feed de Comunicados e Notícias](#6-t006-blogfeed-de-comunicados-e-notícias)
7. [T007: Acompanhamento de Obras](#7-t007-acompanhamento-de-obras)
8. [T008: Área Financeira da Associação](#8-t008-área-financeira-da-associação)
9. [T009: Central de Documentos / Arquivos](#9-t009-central-de-documentos--arquivos)
10. [T010: Livro de Ocorrências](#10-t010-livro-de-ocorrências)
11. [T011: Canal de Críticas, Sugestões e "Fale Conosco"](#11-t011-canal-de-críticas-sugestões-e-fale-conosco)
12. [T012: Análise Comparativa e Melhorias COM21](#12-t012-análise-comparativa-e-melhorias-com21)

---

## 1. T001: Cadastro de Lotes e Vinculação de Usuários

### 1.1 Vision & High-level Scope
The Lot Management module serves as the primary real-estate domain boundary in APRAS. A Lot (or unit/house) represents a physical property within the homeowners association (HOA/condomínio). This module allows administrators to configure blocks (*quadras*), lots (*lotes*), addresses, ideal fractions (*fração ideal*), and land areas. It enables binding system `User` accounts to lots with defined ownership or tenancy roles.

### 1.2 Architecture & Data Model
- **SQLModel Tables**:
  - `Lot` (`id`, `block`, `lot_number`, `address`, `postal_code`, `area_sqm`, `fraction_ideal`, `status`, `notes`, `created_at`, `updated_at`)
  - `UserLotLink` (`id`, `user_id` [FK -> `User.id`], `lot_id` [FK -> `Lot.id`], `association_type`, `is_primary`, `start_date`, `end_date`, `created_at`)
- **Enums**:
  - `LotStatus`: `VACANT`, `OCCUPIED`, `UNDER_CONSTRUCTION`
  - `LotAssociationType`: `PROPRIETARIO` (Owner), `INQUILINO` (Tenant), `RESPONSAVEL_FINANCEIRO` (Financial Responsible), `OUTRO` (Other)
- **Foreign Keys & Indices**:
  - Unique composite index on `Lot(block, lot_number)`.
  - Foreign key `UserLotLink.user_id` -> `user.id` (ON DELETE CASCADE).
  - Foreign key `UserLotLink.lot_id` -> `lot.id` (ON DELETE CASCADE).

### 1.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/lots` — List all lots with optional search/filter by block/status.
  - `POST /api/v1/lots` — Create new lot (Admin/Director).
  - `GET /api/v1/lots/{id}` — Retrieve lot details and linked users.
  - `PUT /api/v1/lots/{id}` — Update lot attributes.
  - `DELETE /api/v1/lots/{id}` — Soft/hard delete lot.
  - `POST /api/v1/lots/{id}/users` — Link user to lot.
  - `DELETE /api/v1/lots/{id}/users/{user_id}` — Unlink user from lot.
  - `POST /api/v1/lots/batch-import` — Upload CSV/Excel to create lots in bulk.
- **Frontend Components & Routing**:
  - Route `/lots` (`LotsPage.tsx`).
  - `LotTable`, `LotFormModal`, `UserLotAssignmentModal`, `LotDetailsView`.
  - Custom React Hook: `useLots.ts`.

### 1.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Can a single user account be linked to multiple lots (e.g. investor owning 3 lots in the HOA)?
  - Is it mandatory for every lot to have at least one primary owner (`is_primary = True`) at all times?
- **Permissions**:
  - Should `Manager` role users be able to view all lots, or only lots assigned to their specific management area?
- **Edge Cases**:
  - When a tenant (`INQUILINO`) link reaches `end_date`, should the user's role/access automatically revert to `GUEST`?

### 1.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Rigid 1-to-1 lot-to-owner database schema; struggles with co-owners or multi-unit investors.
- **APRAS Advantage**: Flexible many-to-many relationship with temporal start/end tracking, historical ownership audits, batch CSV import, and dynamic permission scope.

---

## 2. T002: Cadastro de Moradores por Lote

### 2.1 Vision & High-level Scope
The Resident Management module tracks individual residents living in a lot, regardless of whether they hold an active APRAS user login. This allows HOAs to maintain accurate census records for security, emergency contacts, voting quotas, and gate authorizations. When an unlinked resident registers a system account, the platform matches and links their profile seamlessly.

### 2.2 Architecture & Data Model
- **SQLModel Tables**:
  - `Resident` (`id`, `lot_id` [FK -> `Lot.id`], `user_id` [FK -> `User.id`, Nullable], `full_name`, `cpf`, `rg`, `birth_date`, `phone`, `email`, `relationship_type`, `is_active`, `photo_url`, `notes`, `created_at`, `updated_at`)
- **Enums**:
  - `ResidentRelationship`: `TITULAR` (Primary Resident), `CONJUGE` (Spouse), `FILHO_DEPENDENTE` (Child/Dependent), `INQUILINO` (Tenant), `PARENTE` (Relative), `OUTRO` (Other)
- **Foreign Keys & Indices**:
  - `Resident.lot_id` -> `lot.id` (ON DELETE CASCADE).
  - Index on `Resident.cpf` and `Resident.email` for user account auto-matching.

### 2.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/lots/{lot_id}/residents` — List residents for a specific lot.
  - `POST /api/v1/lots/{lot_id}/residents` — Register a resident under a lot.
  - `PUT /api/v1/residents/{id}` — Update resident details.
  - `DELETE /api/v1/residents/{id}` — Deactivate/delete resident.
  - `POST /api/v1/residents/{id}/link-user` — Manually bind resident profile to a system `User`.
- **Frontend Components & Routing**:
  - Integrated in `LotDetailsPage` (`ResidentTab.tsx`), standalone `ResidentListPage.tsx`.
  - `ResidentFormModal`, `LinkUserModal`, `ResidentCard`.
  - Custom React Hook: `useResidents.ts`.

### 2.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - When a new user registers with a CPF/email matching an existing unlinked `Resident` profile, should auto-linking be automatic or require lot owner / admin validation?
  - Can lot owners edit resident profiles for their lot directly without admin approval?
- **Permissions**:
  - Are residents allowed to view other residents in the same block, or only residents within their own lot?
- **Edge Cases**:
  - How should minor residents (under 18 without CPF) be handled for identification and access passes?

### 2.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Requires manual admin re-entry when a resident becomes a system user, leading to duplicated records.
- **APRAS Advantage**: Smart reconciliation matching CPF/email, self-service profile updates by primary lot owners, and granular relationship tagging.

---

## 3. T003: Cadastro de Visitantes e Prestadores de Serviço

### 3.1 Vision & High-level Scope
This module empowers residents and administrators to pre-authorize visitors, contractors, and service providers (e.g. gardeners, housekeepers, pool technicians). Pre-authorizations support single-entry passes or recurring entry windows with day-of-week restrictions, morning/afternoon/night shifts, and explicit start/end dates. A dedicated gatekeeper interface (*Portaria*) allows real-time check-in, check-out, and verification.

### 3.2 Architecture & Data Model
- **SQLModel Tables**:
  - `Visitor` (`id`, `full_name`, `cpf`, `rg`, `phone`, `company_name`, `photo_url`, `vehicle_plate`, `vehicle_model`, `created_at`, `updated_at`)
  - `VisitorAuthorization` (`id`, `visitor_id` [FK -> `Visitor.id`], `lot_id` [FK -> `Lot.id`], `authorizer_user_id` [FK -> `User.id`], `auth_type`, `allowed_days`, `allowed_shifts`, `valid_from`, `valid_until`, `status`, `notes`, `created_at`)
  - `AccessLog` (`id`, `authorization_id` [FK], `visitor_id` [FK], `lot_id` [FK], `entry_time`, `exit_time`, `gatekeeper_user_id` [FK -> `User.id`], `notes`)
- **Enums**:
  - `AuthorizationType`: `SINGLE` (Única), `PERMANENT` (Permanente/Recorrente)
  - `ShiftType`: `MORNING` (Manhã: 06h-12h), `AFTERNOON` (Tarde: 12h-18h), `NIGHT` (Noite: 18h-06h), `FULL_DAY` (Integral: 24h)
  - `AuthorizationStatus`: `ACTIVE`, `EXPIRED`, `REVOKED`
- **JSON Fields**:
  - `allowed_days`: `["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]`

### 3.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/visitors` — Search visitors by name/CPF/plate.
  - `POST /api/v1/visitors` — Register visitor master profile.
  - `POST /api/v1/authorizations` — Create visitor pre-authorization.
  - `GET /api/v1/lots/{lot_id}/authorizations` — List authorizations for a lot.
  - `PUT /api/v1/authorizations/{id}/revoke` — Revoke authorization immediately.
  - `POST /api/v1/access-logs/check-in` — Register visitor entry at gate.
  - `POST /api/v1/access-logs/check-out` — Register visitor exit.
- **Frontend Components & Routing**:
  - Route `/authorizations` (`VisitorAuthPage.tsx`), `/gate` (`GatekeeperDashboard.tsx`).
  - `PreAuthorizationForm`, `VisitorSearchInput`, `GatekeeperEntryModal`, `AccessLogTimeline`.
  - Custom React Hooks: `useVisitors.ts`, `useGatekeeper.ts`.

### 3.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Should the system auto-generate a temporary QR Code pass sent via WhatsApp/SMS to the visitor upon authorization?
  - Are vehicle license plates mandatory for contractor entry?
- **Permissions**:
  - Can regular residents revoke authorizations created by co-residents of the same lot?
- **Edge Cases**:
  - What occurs when a visitor checks in but does not check out within 24 hours? Should an automated gate alert be triggered?

### 3.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: COM21 visitor modules run on desktop local databases with rigid time slots and zero resident self-service pre-authorization.
- **APRAS Advantage**: Mobile-first resident pre-authorization, real-time push alerts to lot owners on check-in, shift-based access rules, and instant QR pass generation.

---

## 4. T004: Fotos em Cadastros

### 4.1 Vision & High-level Scope
Provides a centralized image handling and secure cloud file storage service for attaching photos across all entity registers (Employees/Staff, Residents, Visitors, Service Providers). Supports direct file upload, live webcam photo capture from gatekeeper terminals, client-side cropping/resizing, and thumbnail generation.

### 4.2 Architecture & Data Model
- **SQLModel Tables**:
  - `MediaAsset` (`id`, `entity_type`, `entity_id`, `storage_provider`, `file_path`, `url`, `thumbnail_url`, `file_size_bytes`, `mime_type`, `width`, `height`, `created_at`, `uploaded_by_id` [FK])
- **Enums**:
  - `EntityType`: `RESIDENT`, `VISITOR`, `EMPLOYEE`, `LOT`, `ANNOUNCEMENT`, `OCCURRENCE`
  - `StorageProvider`: `LOCAL_DISK`, `VERCEL_BLOB`, `AWS_S3`, `CLOUDINARY`
- **File Storage Strategy**:
  - Development: Local storage at `backend/static/uploads/`.
  - Production: S3 / Vercel Blob with CDN delivery and signed access URLs for security.

### 4.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `POST /api/v1/uploads/photo` — Multipart form upload with optional cropping params. Returns `MediaAsset` JSON.
  - `DELETE /api/v1/uploads/photo/{id}` — Remove photo and delete cloud object.
  - `GET /api/v1/uploads/photo/{id}` — Get image metadata / signed URL.
- **Frontend Components & Routing**:
  - `PhotoUploadModal`, `WebcamCaptureDialog` (`react-webcam`), `AvatarCropEditor` (`react-image-crop`), `AvatarWithFallback`.
  - Custom React Hook: `usePhotoUpload.ts`.

### 4.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - What cloud storage provider is preferred for production deployment (AWS S3, Vercel Blob, Cloudinary)?
  - What is the maximum allowed image file size (e.g. 5MB) and acceptable file formats (JPEG, PNG, WebP)?
- **Permissions**:
  - Can residents change their profile photo freely, or does photo change require administrative approval for security control?
- **Edge Cases**:
  - If a user deletes an entity (e.g. Resident), should associated photo files be deleted immediately or preserved for audit compliance?

### 4.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Stores raw low-resolution image blobs directly in SQL database tables, causing massive DB bloat and slow queries.
- **APRAS Advantage**: Offloaded cloud object storage with CDN acceleration, client-side webp compression, webcam support, and unified media management.

---

## 5. T005: Controle de Acesso & Reconhecimento Facial

### 5.1 Vision & High-level Scope
Integrates physical hardware devices (facial recognition cameras, barrier gates, turnstiles, IoT relays) with APRAS. Enables device registration, facial vector template synchronization for residents/staff/visitors, live access monitoring, remote gate triggers, and webhook events from edge hardware.

### 5.2 Architecture & Data Model
- **SQLModel Tables**:
  - `AccessDevice` (`id`, `name`, `device_type`, `ip_address`, `mac_address`, `api_key_hash`, `location`, `status`, `last_ping_at`, `created_at`)
  - `FacialCredential` (`id`, `person_type`, `person_id`, `facial_template_hash`, `sync_status_json`, `created_at`, `updated_at`)
  - `AccessEvent` (`id`, `device_id` [FK], `person_type`, `person_id`, `verification_result`, `confidence_score`, `captured_image_url`, `timestamp`)
- **Enums**:
  - `DeviceType`: `FACIAL_CAMERA`, `BARRIER_GATE`, `TURNSTILE`, `DOOR_LOCK`
  - `DeviceStatus`: `ONLINE`, `OFFLINE`, `MAINTENANCE`
  - `VerificationResult`: `GRANTED`, `DENIED_EXPIRED`, `DENIED_UNKNOWN`, `DENIED_SHIFT`

### 5.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/access-devices` — List registered devices.
  - `POST /api/v1/access-devices` — Register new access controller/camera.
  - `POST /api/v1/access-control/webhooks/{device_id}` — Receive incoming hardware event (face matched / barrier opened).
  - `POST /api/v1/access-control/sync-templates` — Dispatch facial templates to edge devices.
  - `POST /api/v1/access-devices/{id}/remote-unlock` — Execute instant remote door open command.
- **Frontend Components & Routing**:
  - Route `/access-control` (`AccessControlDashboard.tsx`).
  - `LiveGateMonitor`, `DeviceStatusTable`, `FacialSyncStatusModal`, `RemoteUnlockButton`.
  - Custom React Hook: `useAccessControl.ts`.

### 5.4 Open Questions & Edge Cases for User Decision
- **Hardware Integration**:
  - Which facial recognition hardware brands will be deployed (e.g. Intelbras, Control iD, Hikvision, ZKTeco)?
  - Does the hardware support cloud API webhooks or require a local middleware bridge service?
- **Privacy & Security**:
  - Does LGPD (Brazilian General Data Protection Law) consent need to be signed by residents before enrolling facial biometrics?
- **Edge Cases**:
  - How should the system handle gate operations during internet outages (offline device cache strategy)?

### 5.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Requires costly local Windows server software with vendor-locked drivers and slow sync.
- **APRAS Advantage**: Cloud-native webhook API, real-time WebSocket live gate monitoring, multi-vendor device support, and audit event logs.

---

## 6. T006: Blog/Feed de Comunicados e Notícias

### 6.1 Vision & High-level Scope
An Instagram/fotolog-style interactive news feed for association announcements, newsletters, event notices, and official communiqués. Supports rich media attachments (images, PDF documents), text content, comment threads, target lot filtering, read receipts, and publisher role guards.

### 6.2 Architecture & Data Model
- **SQLModel Tables**:
  - `AnnouncementPost` (`id`, `title`, `content`, `category`, `author_id` [FK -> `User.id`], `is_pinned`, `target_user_types_json`, `created_at`, `updated_at`)
  - `PostMedia` (`id`, `post_id` [FK -> `AnnouncementPost.id`], `media_type`, `url`, `caption`, `display_order`)
  - `PostComment` (`id`, `post_id` [FK], `user_id` [FK -> `User.id`], `comment_text`, `is_approved`, `created_at`)
  - `PostReadReceipt` (`id`, `post_id` [FK], `user_id` [FK], `read_at`)
- **Enums**:
  - `PostCategory`: `COMMUNIQUE` (Comunicado), `NEWS` (Notícia), `WARNING` (Aviso), `EVENT` (Evento)
  - `MediaType`: `IMAGE`, `PDF_DOCUMENT`

### 6.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/posts` — Fetch announcements feed with pagination.
  - `POST /api/v1/posts` — Create announcement post with media files.
  - `GET /api/v1/posts/{id}` — Get detailed post with comments.
  - `POST /api/v1/posts/{id}/comments` — Add comment to post.
  - `POST /api/v1/posts/{id}/read` — Mark post as read by user.
  - `DELETE /api/v1/posts/{id}` — Delete post.
- **Frontend Components & Routing**:
  - Route `/feed` (`AnnouncementsFeedPage.tsx`).
  - `PostCard` (with image/PDF carousel), `CreatePostModal`, `CommentThread`, `ReadReceiptsModal`.
  - Custom React Hook: `useFeed.ts`.

### 6.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Who holds posting permissions: Administrators and Directors only, or can specific UserTypes (e.g. Sub-síndicos) publish?
  - Are user comments enabled by default on all posts, or can posting admins toggle comments off per post?
- **Permissions**:
  - Do comments require admin moderation before becoming visible to other residents?
- **Edge Cases**:
  - How should embedded multi-page PDF documents be displayed on mobile devices (inline PDF viewer vs download button)?

### 6.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Static text-only email blasts or bulleted notice boards with zero engagement or visual appeal.
- **APRAS Advantage**: Modern responsive social media feed interface, image carousels, embedded PDF viewer, comment discussions, and read receipt metrics per lot.

---

## 7. T007: Acompanhamento de Obras

### 7.1 Vision & High-level Scope
Dedicated project tracking for HOA capital improvements and construction projects (e.g. clubhouse renovation, paving, security fence installation). Provides physical progress tracking (Done / In Progress / Next Steps), visual completion percentages, financial execution monitoring (budget allocated vs. actual cost executed), and project-specific photo updates.

### 7.2 Architecture & Data Model
- **SQLModel Tables**:
  - `ConstructionProject` (`id`, `title`, `description`, `contractor_name`, `total_budget`, `executed_budget`, `physical_progress_pct`, `start_date`, `estimated_completion_date`, `actual_completion_date`, `status`, `created_at`, `updated_at`)
  - `ProjectMilestone` (`id`, `project_id` [FK -> `ConstructionProject.id`], `title`, `description`, `status`, `due_date`, `completion_date`, `display_order`)
  - `ProjectUpdate` (`id`, `project_id` [FK], `author_id` [FK -> `User.id`], `title`, `content`, `photos_json`, `created_at`)
- **Enums**:
  - `ProjectStatus`: `PLANNED`, `IN_PROGRESS`, `PAUSED`, `COMPLETED`
  - `MilestoneStatus`: `DONE` (Feito), `IN_PROGRESS` (Em Andamento), `NEXT_STEPS` (Próximos Passos)

### 7.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/projects` — List construction projects.
  - `POST /api/v1/projects` — Create project.
  - `GET /api/v1/projects/{id}` — Detailed project view with milestones and financial summary.
  - `PUT /api/v1/projects/{id}/milestones` — Update milestone progress.
  - `POST /api/v1/projects/{id}/updates` — Post photo/progress log.
- **Frontend Components & Routing**:
  - Route `/projects` (`ConstructionTrackerPage.tsx`).
  - `ProjectSummaryCard`, `MilestoneTimeline`, `BudgetVsActualProgressBar`, `ProjectUpdateFeed`.
  - Custom React Hook: `useConstructionProjects.ts`.

### 7.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Should residents be able to submit questions/comments on specific construction updates?
  - Is financial detail visibility restricted to board members, or visible to all HOA members for transparency?
- **Integrations**:
  - Should expenses registered under a construction milestone automatically link to the Financial Module (Domain 8)?
- **Edge Cases**:
  - How are cost overruns (executed budget exceeding total budget) visually highlighted and reported?

### 7.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: No physical or financial project tracking; updates buried in meeting minutes documents.
- **APRAS Advantage**: Visual progress bars, milestone timelines (Feito/Em Andamento/Próximos Passos), side-by-side budget vs actual graphs, and visual site photo timeline updates.

---

## 8. T008: Área Financeira da Associação

### 8.1 Vision & High-level Scope
Provides a financial management and transparency portal for the HOA. Displays overall financial health, current cash balance across bank accounts, monthly inflow/outflow statements (*demonstrativo de entradas e saídas*), budget vs. actual execution per category item, and 1-click drill-down to supporting invoices/receipts (*notas fiscais/comprovantes*).

### 8.2 Architecture & Data Model
- **SQLModel Tables**:
  - `BankAccount` (`id`, `bank_name`, `account_number`, `agency`, `initial_balance`, `current_balance`, `is_active`)
  - `FinancialCategory` (`id`, `name`, `code`, `type`, `budget_allocated`, `created_at`)
  - `FinancialTransaction` (`id`, `category_id` [FK -> `FinancialCategory.id`], `bank_account_id` [FK -> `BankAccount.id`], `transaction_type`, `amount`, `transaction_date`, `description`, `vendor_or_payer`, `invoice_number`, `document_url`, `status`, `created_at`)
- **Enums**:
  - `TransactionType`: `INCOME` (Entrada), `EXPENSE` (Saída)
  - `TransactionStatus`: `PAID`, `PENDING`, `CANCELLED`

### 8.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/financial/summary` — Total cash balance, monthly income, monthly expenses.
  - `GET /api/v1/financial/transactions` — Filter transactions by date, category, type.
  - `POST /api/v1/financial/transactions` — Create transaction record with document upload.
  - `GET /api/v1/financial/budget-vs-actual` — Inflow/outflow vs budget per line item.
  - `GET /api/v1/financial/transactions/{id}/receipt` — Download/view invoice attachment.
- **Frontend Components & Routing**:
  - Route `/financial` (`FinancialDashboardPage.tsx`).
  - `CashBalanceCards`, `InflowOutflowChart`, `BudgetVsActualTable`, `InvoiceDrillDownModal`.
  - Custom React Hook: `useFinancials.ts`.

### 8.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Does APRAS generate individual resident payment slips (*boletos/PIX*), or is this financial module strictly focused on HOA accounting transparency?
  - Will financial data be imported via OFX bank files or accounting system APIs?
- **Permissions**:
  - Are standard residents allowed to see individual vendor names and invoice documents, or aggregated totals only?
- **Edge Cases**:
  - How are recurring monthly utility expenses (water, electricity, security) handled when invoices arrive late?

### 8.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Generates static, cryptic PDF balance sheets (*balancetes*) once a month that residents find difficult to comprehend.
- **APRAS Advantage**: Real-time visual dashboard, interactive budget vs. actual variance analysis, and 1-click drill-down to original tax invoice PDF receipts.

---

## 9. T009: Central de Documentos / Arquivos

### 9.1 Vision & High-level Scope
A structured digital document repository for legal, financial, and operational association files. Organizes documents into hierarchical folders (e.g. Balance Sheets, Contracts, Meeting Minutes, Internal Bylaws/Regimento Interno) with role-gated folder permissions, full-text metadata search, inline PDF previewing, and download tracking.

### 9.2 Architecture & Data Model
- **SQLModel Tables**:
  - `DocumentFolder` (`id`, `name`, `description`, `parent_id` [FK -> `DocumentFolder.id`, Nullable], `allowed_roles_json`, `created_at`)
  - `AssociationDocument` (`id`, `folder_id` [FK -> `DocumentFolder.id`], `title`, `description`, `file_url`, `file_size_bytes`, `mime_type`, `publication_year`, `publication_month`, `tags_json`, `uploaded_by_id` [FK], `created_at`)
  - `DocumentDownloadLog` (`id`, `document_id` [FK], `user_id` [FK], `downloaded_at`)
- **JSON Fields**:
  - `allowed_roles_json`: `["ADMINISTRATOR", "DIRECTOR", "RESIDENT"]`

### 9.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/documents/folders` — Fetch folder hierarchy tree.
  - `POST /api/v1/documents/folders` — Create document folder (Admin).
  - `GET /api/v1/documents` — Search and filter documents by folder/year/tags.
  - `POST /api/v1/documents/upload` — Upload document file with metadata.
  - `DELETE /api/v1/documents/{id}` — Delete document.
  - `GET /api/v1/documents/{id}/download` — Log download and return file stream/URL.
- **Frontend Components & Routing**:
  - Route `/documents` (`DocumentCenterPage.tsx`).
  - `FolderTreeSidebar`, `DocumentGridTable`, `PDFViewerModal`, `DocumentUploadModal`.
  - Custom React Hook: `useDocuments.ts`.

### 9.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Should document versioning be supported (e.g. keeping v1 and v2 of Regimento Interno with change logs)?
  - Are confidential folders required for Board-only internal communications?
- **Edge Cases**:
  - How should large PDF files (e.g. 50MB architectural blueprints) be streamed and cached?

### 9.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Unorganized flat file download list with zero folder structure, search, or inline preview.
- **APRAS Advantage**: Nested folder tree, role-gated folder security, inline browser PDF preview, metadata search, and download audit logs.

---

## 10. T010: Livro de Ocorrências

### 10.1 Vision & High-level Scope
Digital occurrence book enabling residents to log complaints, maintenance reports, noise issues, parking violations, or rule infractions. Every occurrence generates a unique protocol tracking number. Administration can assign tickets, update status (Open -> Under Review -> In Progress -> Resolved), record internal notes, attach photo evidence, and measure resolution time.

### 10.2 Architecture & Data Model
- **SQLModel Tables**:
  - `Occurrence` (`id`, `protocol_number`, `lot_id` [FK -> `Lot.id`], `reporter_user_id` [FK -> `User.id`], `category`, `title`, `description`, `photo_urls_json`, `status`, `priority`, `assigned_to_id` [FK -> `User.id`, Nullable], `resolution_notes`, `created_at`, `updated_at`, `resolved_at`)
  - `OccurrenceTimeline` (`id`, `occurrence_id` [FK -> `Occurrence.id`], `actor_id` [FK -> `User.id`], `status_from`, `status_to`, `note`, `is_internal_only`, `created_at`)
- **Enums**:
  - `OccurrenceCategory`: `NOISE` (Barulho), `MAINTENANCE` (Manutenção), `SECURITY` (Segurança), `PARKING` (Estacionamento), `RULES_VIOLATION` (Regimento Interno), `OTHER` (Outro)
  - `OccurrenceStatus`: `OPEN`, `UNDER_REVIEW`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`
  - `OccurrencePriority`: `LOW`, `MEDIUM`, `HIGH`, `URGENT`

### 10.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/occurrences` — List occurrences with status/category filters.
  - `POST /api/v1/occurrences` — Submit new occurrence ticket (auto-generates protocol).
  - `GET /api/v1/occurrences/{id}` — Get occurrence details and timeline log.
  - `PUT /api/v1/occurrences/{id}/status` — Update ticket status and assign owner.
  - `POST /api/v1/occurrences/{id}/notes` — Add public or internal note.
- **Frontend Components & Routing**:
  - Route `/occurrences` (`OccurrenceBookPage.tsx`).
  - `OccurrenceTable`, `NewOccurrenceModal`, `OccurrenceDetailsView`, `OccurrenceTimelineLog`.
  - Custom React Hook: `useOccurrences.ts`.

### 1.4 Open Questions & Edge Cases for User Decision
- **Business Rules**:
  - Are anonymous occurrence reports allowed?
  - Are occurrences strictly private between the reporting lot and administration, or public to all residents?
- **SLAs**:
  - Should the system trigger warning notifications if an occurrence remains unaddressed past 48 hours?

### 10.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Paper book or basic text area with zero protocol tracking, timeline audits, or photo attachments.
- **APRAS Advantage**: Unique protocol sequence numbers, photo evidence attachments, private vs public notes, status timelines, and resolution SLA tracking.

---

## 11. T011: Canal de Críticas, Sugestões e "Fale Conosco"

### 11.1 Vision & High-level Scope
A dedicated feedback channel for general dialogue, constructive critiques, community suggestions, and direct communication with the board (*síndico e diretoria*). Distinct from operational tickets in Domain 10, this channel focuses on governance, ideas, and general inquiries, with options for anonymous feedback and direct response threads.

### 11.2 Architecture & Data Model
- **SQLModel Tables**:
  - `FeedbackMessage` (`id`, `user_id` [FK -> `User.id`], `lot_id` [FK -> `Lot.id`, Nullable], `feedback_type`, `subject`, `message`, `is_anonymous`, `status`, `response_text`, `responded_by_id` [FK -> `User.id`, Nullable], `created_at`, `responded_at`)
- **Enums**:
  - `FeedbackType`: `CRITIQUE` (Crítica), `SUGGESTION` (Sugestão), `GENERAL_CONTACT` (Fale Conosco), `COMPLIMENT` (Elogio)
  - `FeedbackStatus`: `NEW`, `READ`, `IN_ANALYSIS`, `ANSWERED`, `ARCHIVED`

### 11.3 API & Frontend Integration Points
- **Backend Endpoints**:
  - `GET /api/v1/feedback` — List feedback messages (Admin/Director inbox).
  - `POST /api/v1/feedback` — Submit feedback message.
  - `GET /api/v1/feedback/{id}` — Retrieve feedback details and response.
  - `POST /api/v1/feedback/{id}/respond` — Submit administrative reply.
- **Frontend Components & Routing**:
  - Route `/contact` (`ContactUsPage.tsx`), `/admin/feedback` (`FeedbackInboxPage.tsx`).
  - `FeedbackForm`, `FeedbackInboxTable`, `ResponseModal`.
  - Custom React Hook: `useFeedback.ts`.

### 11.4 Open Questions & Edge Cases for User Decision
- **Workflow Distinction**:
  - How should administration route a "Fale Conosco" message if it turns out to be an urgent maintenance incident? (Option: 1-click conversion from Feedback to Occurrence).
- **Anonymity**:
  - When a user selects `is_anonymous = True`, should their user ID and lot ID be completely omitted from the database record?
- **Public Proposals**:
  - Can highly upvoted suggestions be converted into official community polls?

### 11.5 Benchmark & Improvements Relative to COM21
- **COM21 Limit**: Bundles complaints, suggestions, and queries into one unorganized inbox.
- **APRAS Advantage**: Separate governance channel, anonymous submission toggles, direct reply threads, sentiment tagging, and option to convert feedback into actionable occurrences.

---

## 12. T012: Análise Comparativa e Melhorias COM21

### 12.1 Vision & High-level Scope
Consolidated benchmark analysis comparing traditional COM21 capabilities against APRAS. Defines specifications for high-impact extended features missing in legacy systems, including Package Delivery Tracking (*Encomendas da Portaria*), Common Area Reservations (*Reserva de Áreas Comuns*), and Mobile Web Push notifications.

### 12.2 Comparative Parity & Feature Matrix

| Feature Domain | COM21 Capability | APRAS Enhanced Architecture | Advantage |
| :--- | :--- | :--- | :--- |
| **Lots & Residents** | Fixed 1-to-1 lot-owner records; manual entry | Many-to-many temporal links; CPF auto-matching | **APRAS** |
| **Visitor Control** | Desktop-only local DB gate software | Mobile pre-authorization, QR pass, shift rules | **APRAS** |
| **Photos & Facial** | Low-res DB BLOBs; legacy serial hardware | Cloud storage CDN, webcam capture, Webhooks API | **APRAS** |
| **Announcements Feed** | Static plain-text email blasts | Social media feed, carousels, PDF viewer, comments | **APRAS** |
| **Construction Tracking** | Not available | Milestones (Done/In Progress), budget progress bar | **APRAS** |
| **Financial Transparency** | Static monthly PDF balance sheet | Real-time cash balance, budget vs actual, PDF drill-down | **APRAS** |
| **Document Center** | Flat file download list | Nested folder tree, role-gated access, inline PDF preview | **APRAS** |
| **Occurrence Book** | Basic text box; no protocol numbers | Protocol sequence, photo evidence, SLA tracking | **APRAS** |
| **Feedback Channel** | Single combined contact inbox | Separated governance channel, anonymous toggle, replies | **APRAS** |
| **Package Tracking** | Basic desktop receipt log | Barcode scanner, push notifications, resident sign-out | **Planned (T012)** |
| **Area Reservations** | Rigid paper/phone calendar | Interactive rules, availability grid, approval workflow | **Planned (T012)** |

### 12.3 Extended Feature Specifications (T012 Roadmap)

#### 12.3.1 Package Delivery Tracking (*Controle de Encomendas*)
- **Data Model**: `PackageReceipt` (`id`, `lot_id` [FK], `resident_id` [FK], `tracking_code`, `carrier_name`, `received_at`, `gatekeeper_id` [FK], `pickup_at`, `picked_up_by_id` [FK], `status` [`RECEIVED`, `PICKED_UP`]).
- **Workflow**: Gatekeeper logs package -> System fires push/email notification with barcode -> Resident collects package and signs digitally on tablet.

#### 12.3.2 Common Area Reservations (*Reserva de Áreas Comuns*)
- **Data Model**: `CommonArea` (`id`, `name`, `capacity`, `fee_amount`, `rules_text`), `Reservation` (`id`, `area_id` [FK], `lot_id` [FK], `reservation_date`, `status` [`PENDING`, `APPROVED`, `CANCELLED`]).
- **Workflow**: Resident checks real-time availability grid -> Requests date -> System checks clean-up windows and lot pending dues -> Auto-approves or routes to admin.

---

## 13. Summary Matrix of Registered Meridian Tasks

| Task ID | Title | Initial Status | Blocked By | Spec Path |
| :--- | :--- | :--- | :--- | :--- |
| **T001** | Cadastro de Lotes e Vinculação de Usuários | `specreview` | None | `docs/tasks/T001-spec.md` |
| **T002** | Cadastro de Moradores por Lote | `blocked` | `T001` | `docs/tasks/T002-spec.md` |
| **T003** | Cadastro de Visitantes e Prestadores de Serviço | `blocked` | `T001` | `docs/tasks/T003-spec.md` |
| **T004** | Gestão e Armazenamento de Fotos nos Cadastros | `backlog` | None | `docs/tasks/T004-spec.md` |
| **T005** | Controle de Acesso e Reconhecimento Facial | `blocked` | `T003`, `T004` | `docs/tasks/T005-spec.md` |
| **T006** | Blog/Feed de Comunicados e Notícias | `blocked` | `T004` | `docs/tasks/T006-spec.md` |
| **T007** | Acompanhamento Físico e Financeiro de Obras | `backlog` | None | `docs/tasks/T007-spec.md` |
| **T008** | Área e Dashboard Financeiro da Associação | `backlog` | None | `docs/tasks/T008-spec.md` |
| **T009** | Central de Documentos e Arquivos da Associação | `backlog` | None | `docs/tasks/T009-spec.md` |
| **T010** | Livro de Ocorrências e Atendimento de Reclamações | `blocked` | `T001` | `docs/tasks/T010-spec.md` |
| **T011** | Canal de Críticas, Sugestões e Fale Conosco | `backlog` | None | `docs/tasks/T011-spec.md` |
| **T012** | Análise Comparativa e Recursos Avançados COM21 | `backlog` | None | `docs/tasks/T012-spec.md` |

---

## 14. Next Steps & Instructions for the User

1. **Review Open Questions**: Please examine the open questions and edge cases highlighted under sections 1.4 through 11.4 in [docs/features_planning_and_questions.md](file:///Users/heitor/workspace/apras/docs/features_planning_and_questions.md).
2. **Drive Task Execution**: Once decisions on business rules are confirmed, the Meridian PM will initiate **Fluxo A** (spec-generator ↔ spec-reviewer) starting with `T001`, producing the detailed task specification in `docs/tasks/T001-spec.md`.
