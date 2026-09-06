import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";

/**
 * The notified unit's written defense (ER-7).
 *
 * Rendered **only inside `/my-infractions`**, which already lists nothing but
 * the caller's own lots — so §7.5's 403 is unreachable from the UI and this
 * component needs no client-side lot check. What it does need is the deadline
 * state, because a closed deadline is a 409 the resident should never have to
 * discover by submitting.
 */
export const ContestationForm: React.FC<{
  defenseDueOn: string | null;
  onSubmit: (body: string) => void;
  isSubmitting?: boolean;
}> = ({ defenseDueOn, onSubmit, isSubmitting = false }) => {
  const { t } = useTranslation();
  const [body, setBody] = useState("");

  const open =
    defenseDueOn !== null &&
    new Date(`${defenseDueOn}T23:59:59`) >= new Date();

  if (!open) {
    return (
      <p
        className="text-sm text-gray-500"
        data-testid="contestation-unavailable"
      >
        {defenseDueOn === null
          ? t("infractions.contestation.noDeadline")
          : t("infractions.contestation.deadlinePassed", { date: defenseDueOn })}
      </p>
    );
  }

  return (
    <div className="space-y-2" data-testid="contestation-form">
      <p className="text-sm text-gray-500">
        {t("infractions.contestation.deadlineOpen", { date: defenseDueOn })}
      </p>
      <textarea
        className="w-full rounded-lg border border-gray-200 p-2 text-sm"
        aria-label={t("infractions.contestation.body")}
        value={body}
        onChange={(event) => setBody(event.target.value)}
      />
      <Button
        data-testid="submit-contestation"
        disabled={!body.trim() || isSubmitting}
        onClick={() => onSubmit(body)}
      >
        {t("infractions.contestation.submit")}
      </Button>
    </div>
  );
};

export default ContestationForm;
