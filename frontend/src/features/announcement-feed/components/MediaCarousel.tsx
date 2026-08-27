import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import type { AnnouncementMedia } from "../../../types/announcement";

interface MediaCarouselProps {
  media: AnnouncementMedia[];
}

export const MediaCarousel: React.FC<MediaCarouselProps> = ({ media }) => {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);

  if (!media || media.length === 0) return null;

  const current = media[index];
  const hasMultiple = media.length > 1;

  const goPrev = () => setIndex((i) => (i - 1 + media.length) % media.length);
  const goNext = () => setIndex((i) => (i + 1) % media.length);

  return (
    <div
      className="relative w-full bg-gray-100 rounded-lg overflow-hidden"
      data-testid="media-carousel"
    >
      {current.media_type === "IMAGE" ? (
        <img
          src={current.url}
          alt={t("announcements.media_alt", "Anexo do comunicado")}
          className="w-full max-h-96 object-cover"
        />
      ) : (
        <a
          href={current.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 p-6 bg-white hover:bg-gray-50 transition-colors"
          data-testid="pdf-attachment-link"
        >
          <FileText className="w-8 h-8 text-red-600" />
          <span className="text-sm font-semibold text-gray-800">
            {t("announcements.open_pdf", "Abrir documento PDF")}
          </span>
        </a>
      )}

      {hasMultiple && (
        <>
          <button
            type="button"
            onClick={goPrev}
            aria-label={t("announcements.carousel_prev", "Anterior")}
            className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 bg-white/80 hover:bg-white rounded-full shadow"
          >
            <ChevronLeft className="w-4 h-4 text-gray-700" />
          </button>
          <button
            type="button"
            onClick={goNext}
            aria-label={t("announcements.carousel_next", "Próximo")}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-white/80 hover:bg-white rounded-full shadow"
          >
            <ChevronRight className="w-4 h-4 text-gray-700" />
          </button>
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
            {media.map((m, i) => (
              <span
                key={m.id}
                className={`w-1.5 h-1.5 rounded-full ${
                  i === index ? "bg-indigo-600" : "bg-white/70"
                }`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};
