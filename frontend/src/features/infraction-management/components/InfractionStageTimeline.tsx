import React from "react";
import { useTranslation } from "react-i18next";
import type { InfractionTimelineEntry } from "../../../types/infraction";

/**
 * The merged, **read-only** append-only history (ER-3).
 *
 * There is deliberately no edit and no delete control anywhere in this
 * component, and there is no route that would accept one: a mistaken stage is
 * corrected by a subsequent stage whose note says so.
 */
export const InfractionStageTimeline: React.FC<{
  entries: InfractionTimelineEntry[];
}> = ({ entries }) => {
  const { t } = useTranslation();

  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-500" data-testid="timeline-empty">
        {t("infractions.timeline.empty")}
      </p>
    );
  }

  return (
    <ol className="space-y-3" data-testid="infraction-timeline">
      {entries.map((entry) => (
        <li
          key={entry.id}
          data-testid={`timeline-${entry.kind.toLowerCase()}`}
          className="rounded-lg border border-gray-100 p-3"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-gray-900">
              {entry.kind === "STAGE"
                ? t(`infractions.actions.${entry.action}`)
                : t("infractions.timeline.contestation")}
            </span>
            <span className="text-xs text-gray-400">
              {new Date(entry.at).toLocaleString()}
            </span>
          </div>

          {entry.actor && (
            <div className="text-xs text-gray-500">{entry.actor.full_name}</div>
          )}

          {entry.note && (
            <p className="mt-1 text-sm text-gray-700">{entry.note}</p>
          )}

          {entry.fine_amount !== null && entry.fine_amount !== undefined && (
            <div className="mt-1 text-sm text-gray-900">
              {t("infractions.timeline.fineAmount")}:{" "}
              {entry.fine_amount.toFixed(2)}
              {entry.fine_amount_overridden && (
                <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                  {t("infractions.timeline.overridden")}
                </span>
              )}
            </div>
          )}

          {entry.defense_due_on && (
            <div className="mt-1 text-xs text-gray-500">
              {t("infractions.timeline.defenseDueOn")}: {entry.defense_due_on}
            </div>
          )}

          {/* Read-only, for both kinds: a stage can carry evidence just as a
              contestation carries its attachments. No edit, no delete and no
              permission gate — display is not governed by
              `uploads:photo_create`. */}
          {entry.attachment_urls.length > 0 && (
            <div className="mt-2" data-testid="timeline-attachments">
              <span className="text-xs text-gray-500">
                {t("infractions.attachments.timelineTitle")}
              </span>
              <ul className="mt-1 space-y-1 text-sm">
                {entry.attachment_urls.map((url, index) => (
                  <li key={url} className="flex items-center gap-2">
                    <img
                      src={url}
                      alt={t("infractions.attachments.imageAlt", {
                        index: index + 1,
                      })}
                      className="h-10 w-10 rounded object-cover"
                    />
                    <a className="text-indigo-600 underline" href={url}>
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {entry.kind === "STAGE" && entry.suggestion_followed === false && (
            <div className="mt-1 text-xs text-amber-700">
              {t("infractions.timeline.deviation")}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
};

export default InfractionStageTimeline;
