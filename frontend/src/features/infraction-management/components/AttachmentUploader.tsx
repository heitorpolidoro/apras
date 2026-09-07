import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { parseApiError } from "../../../api/errors";
import {
  UPLOAD_ACCEPT,
  UPLOAD_ALLOWED_MIME_TYPES,
  UPLOAD_MAX_FILE_SIZE_BYTES,
  UPLOAD_PHOTO_PERMISSION,
} from "../../../api/uploads";
import { useUploadPhoto } from "../../media-management/hooks/useMediaAssets";
import { usePermissionSet } from "../../user-administration/access/useCanAccess";
import type { EntityType } from "../../../types/media_asset";

/**
 * Both infraction forms attach to an infraction, so the vocabulary is this one.
 * Declared here and asserted against the server's `EntityType.INFRACTION` by
 * the two-sided pin (`uploadContract.test.tsx` ↔
 * `backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`).
 */
export const INFRACTION_ENTITY_TYPE: EntityType = "INFRACTION";

/** `image/jpeg` → `JPEG`. Derived, so a wider server set widens the hint. */
const typeLabels = UPLOAD_ALLOWED_MIME_TYPES.map((mime) =>
  mime.split("/")[1].toUpperCase(),
).join(", ");

const megabytes = (bytes: number) => `${Math.round(bytes / (1024 * 1024))} MB`;
const preciseMegabytes = (bytes: number) =>
  `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

/**
 * The attachment control both infraction forms use (APRAS-53).
 *
 * One component and not two: the evidence field of `NewInfractionModal` and
 * the attachment field of `ContestationForm` differ in the label and in
 * whether the infraction already exists, and nothing else. One component is
 * also what makes the permission gate impossible to apply to one form and
 * forget on the other.
 *
 * **The gate.** Since APRAS-51 `POST /api/v1/uploads/photo` demands
 * `uploads:photo_create`, and nothing seeds it (post-F5 doctrine), so a
 * resident writing a defense may simply not hold it. Without the permission
 * the control is replaced by a sentence — not a disabled input, which would
 * invite the reader to look for the switch that enables it. The surrounding
 * form stays submittable: `attachment_urls` has `default_factory=list`, and
 * blocking submit would turn an attachment permission into a permission to
 * contest.
 *
 * It reads `usePermissionSet()` — the **real** set — and deliberately not
 * `useEffectivePermissionSet()`: the upload is made with the real token, so a
 * simulated resident that showed the control would produce exactly the 403 the
 * gate exists to avoid. Attaching a file is authorization, and authorization
 * reads the real set.
 *
 * The gate is convenience and never a guarantee, so the server's own refusals
 * — the two 400s and the 403 of a permission revoked between load and click —
 * are rendered inline through the module's `parseApiError`, with no branch on
 * status.
 */
export const AttachmentUploader: React.FC<{
  /** URLs already uploaded; the parent form owns the state. */
  value: string[];
  onChange: (urls: string[]) => void;
  /** Absent on creation (the infraction does not exist yet). */
  entityId?: string;
  /** Resolved by the parent: evidence vs. attachments. */
  label: string;
  disabled?: boolean;
}> = ({ value, onChange, entityId, label, disabled = false }) => {
  const { t } = useTranslation();
  const { has, isLoading } = usePermissionSet();
  const upload = useUploadPhoto();
  const [error, setError] = useState<string | null>(null);
  const [uploadingName, setUploadingName] = useState<string | null>(null);

  if (isLoading) {
    // Fail closed while `/permissions/me` is in flight: never a control that
    // appears and then disappears.
    return (
      <p className="text-sm text-gray-500" data-testid="attachment-gate-loading">
        {t("infractions.attachments.loading")}
      </p>
    );
  }

  if (!has(UPLOAD_PHOTO_PERMISSION)) {
    return (
      <p className="text-sm text-gray-500" data-testid="attachment-unavailable">
        {t("infractions.attachments.permissionRequired")}
      </p>
    );
  }

  const accepted: readonly string[] = UPLOAD_ALLOWED_MIME_TYPES;

  const handleFiles = async (files: File[]) => {
    setError(null);
    // Sequential, not `Promise.all`: it gives the resulting list the order the
    // caller chose, and keeps the assertion of that order readable.
    const uploaded: string[] = [];
    for (const file of files) {
      if (!accepted.includes(file.type)) {
        setError(
          t("infractions.attachments.unsupportedType", { name: file.name }),
        );
        continue;
      }
      if (file.size > UPLOAD_MAX_FILE_SIZE_BYTES) {
        setError(
          t("infractions.attachments.tooLarge", {
            name: file.name,
            size: preciseMegabytes(file.size),
            limit: megabytes(UPLOAD_MAX_FILE_SIZE_BYTES),
          }),
        );
        continue;
      }
      setUploadingName(file.name);
      try {
        const created = await upload.mutateAsync({
          file,
          entityType: INFRACTION_ENTITY_TYPE,
          entityId,
        });
        uploaded.push(created.url);
      } catch (err) {
        setError(
          parseApiError(err, t, {
            validationError: "infractions.errors.validation",
            genericError: "infractions.errors.generic",
          }),
        );
      } finally {
        setUploadingName(null);
      }
    }
    if (uploaded.length > 0) {
      onChange([...value, ...uploaded]);
    }
  };

  const busy = uploadingName !== null;

  return (
    <div className="space-y-2" data-testid="attachment-uploader">
      <label className="block text-sm">
        <span className="text-gray-500">{label}</span>
        <input
          type="file"
          multiple
          accept={UPLOAD_ACCEPT}
          aria-label={label}
          title={t("infractions.attachments.add")}
          data-testid="attachment-file-input"
          disabled={disabled || busy}
          className="mt-1 block w-full text-sm"
          onChange={(event) => {
            const chosen = Array.from(event.target.files ?? []);
            // Let the same file be chosen again after a refusal.
            event.target.value = "";
            void handleFiles(chosen);
          }}
        />
      </label>

      <p className="text-xs text-gray-500" data-testid="attachment-hint">
        {t("infractions.attachments.hint", {
          types: typeLabels,
          limit: megabytes(UPLOAD_MAX_FILE_SIZE_BYTES),
        })}
      </p>

      {busy && (
        <p className="text-xs text-gray-500" data-testid="attachment-uploading">
          {t("infractions.attachments.uploading", { name: uploadingName })}
        </p>
      )}

      {error && (
        <p
          className="rounded-lg bg-red-50 p-2 text-sm text-red-700"
          role="alert"
          data-testid="attachment-error"
        >
          {error}
        </p>
      )}

      {value.length === 0 && !busy ? (
        <p className="text-xs text-gray-400" data-testid="attachment-none">
          {t("infractions.attachments.none")}
        </p>
      ) : (
        <ul className="space-y-1">
          {value.map((url, index) => (
            <li
              key={url}
              data-testid="attachment-chip"
              className="flex items-center gap-2 text-sm"
            >
              <img
                src={url}
                alt={t("infractions.attachments.imageAlt", {
                  index: index + 1,
                })}
                className="h-10 w-10 rounded object-cover"
              />
              <a className="flex-1 truncate text-indigo-600 underline" href={url}>
                {url}
              </a>
              <button
                type="button"
                data-testid="attachment-remove"
                aria-label={t("infractions.attachments.remove")}
                className="text-xs text-gray-500 underline"
                disabled={disabled}
                onClick={() =>
                  // Only the list is edited. Deleting the stored asset needs
                  // `uploads:delete`, which the resident contesting may not
                  // hold — the call would 403 on the happy path.
                  onChange(value.filter((current) => current !== url))
                }
              >
                {t("infractions.attachments.remove")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AttachmentUploader;
