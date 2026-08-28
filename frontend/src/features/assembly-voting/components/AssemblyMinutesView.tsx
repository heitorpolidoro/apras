import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { useAssemblyMinutes, useSaveAssemblyMinutes } from "../hooks/useVoting";
import type { AssemblyRead } from "../../../types/voting";

interface AssemblyMinutesViewProps {
  assembly: AssemblyRead;
}

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

/**
 * Minutes viewer.
 *
 * The server renders standalone HTML (printed to PDF by the browser), so
 * it is displayed in a sandboxed iframe rather than injected into the app
 * document.
 */
const AssemblyMinutesView: React.FC<AssemblyMinutesViewProps> = ({
  assembly,
}) => {
  const { t } = useTranslation();
  const isClosed = assembly.status === "CLOSED";
  const { data: minutes, isLoading } = useAssemblyMinutes(
    isClosed ? assembly.id : undefined,
  );
  const saveMutation = useSaveAssemblyMinutes();
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!isClosed) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("voting.minutes.unavailable")}
      </p>
    );
  }

  const handleSave = () => {
    setFeedback(null);
    saveMutation.mutate(assembly.id, {
      onSuccess: () => setFeedback(t("voting.minutes.saved")),
      onError: (err: ApiError) =>
        setFeedback(
          err.response?.data?.detail || t("voting.minutes.errorSaving"),
        ),
    });
  };

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">{t("voting.minutes.title")}</h3>
        <Button
          type="button"
          size="sm"
          onClick={handleSave}
          disabled={saveMutation.isPending}
        >
          {t("voting.minutes.save")}
        </Button>
      </div>

      {feedback && <p className="text-sm text-muted-foreground">{feedback}</p>}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">
          {t("voting.minutes.loading")}
        </p>
      ) : (
        <iframe
          title={t("voting.minutes.title")}
          data-testid="minutes-frame"
          sandbox=""
          srcDoc={minutes ?? ""}
          className="w-full h-[60vh] rounded-md border border-border/60 bg-white"
        />
      )}
    </section>
  );
};

export default AssemblyMinutesView;
