import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { AlertModal } from "../../../components/ui/alert-modal";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import {
  useReservableSpaces,
  useSpaceReservations,
  useCreateSpaceReservation,
  useApproveReservation,
  useRejectReservation,
  useCancelReservation,
} from "../hooks/useReservations";
import type { SpaceReservationRead } from "../../../types/reservation";

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

const statusBadgeClass = (status: string) => {
  switch (status) {
    case "CONFIRMED":
      return "bg-emerald-100 text-emerald-700";
    case "PENDING":
      return "bg-amber-100 text-amber-700";
    case "REJECTED":
      return "bg-destructive/10 text-destructive";
    case "CANCELLED":
      return "bg-slate-100 text-slate-500";
    default:
      return "bg-slate-100 text-slate-500";
  }
};

const canCancelClientSide = (reservation: SpaceReservationRead): boolean => {
  if (reservation.status !== "PENDING" && reservation.status !== "CONFIRMED") {
    return false;
  }
  return new Date(reservation.start_time).getTime() > Date.now();
};

const SpaceBookingPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const isGuest = role === UserRole.GUEST;
  const isStaff = role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;

  const { data: spaces, isLoading: spacesLoading } = useReservableSpaces();
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);

  const { data: spaceReservations } = useSpaceReservations(
    selectedSpaceId ?? undefined,
  );
  const { data: myReservations } = useSpaceReservations(undefined, true);
  const { data: pendingApprovals } = useSpaceReservations(undefined, false);

  const createMutation = useCreateSpaceReservation();
  const approveMutation = useApproveReservation();
  const rejectMutation = useRejectReservation();
  const cancelMutation = useCancelReservation();

  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setStartTime("");
    setEndTime("");
    setNotes("");
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSpaceId || !startTime || !endTime) return;
    setError(null);
    createMutation.mutate(
      {
        space_id: selectedSpaceId,
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => resetForm(),
        onError: (err: ApiError) => {
          setError(
            err.response?.data?.detail || t("reservations.booking.errorCreating"),
          );
        },
      },
    );
  };

  const handleCancel = (id: string) => {
    setError(null);
    cancelMutation.mutate(id, {
      onError: (err: ApiError) => {
        setError(err.response?.data?.detail || t("reservations.booking.errorCancelling"));
      },
    });
  };

  const handleApprove = (id: string) => {
    setError(null);
    approveMutation.mutate(id, {
      onError: (err: ApiError) => {
        setError(err.response?.data?.detail || t("reservations.booking.errorApproving"));
      },
    });
  };

  const handleReject = (id: string) => {
    setError(null);
    rejectMutation.mutate(id, {
      onError: (err: ApiError) => {
        setError(err.response?.data?.detail || t("reservations.booking.errorRejecting"));
      },
    });
  };

  const sortedSpaceReservations = [...(spaceReservations ?? [])].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
  );

  const pendingList = (pendingApprovals ?? []).filter((r) => r.status === "PENDING");

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-4">
          {t("reservations.booking.title")}
        </h1>

        <AlertModal
          open={!!error}
          onClose={() => setError(null)}
          variant="destructive"
          title="Erro"
          message={error ?? ""}
        />

        {spacesLoading ? (
          <p className="text-sm text-muted-foreground">
            {t("reservations.booking.loadingSpaces")}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2 mb-4">
            {(spaces ?? []).map((space) => (
              <Button
                key={space.id}
                type="button"
                size="sm"
                variant={selectedSpaceId === space.id ? "default" : "outline"}
                onClick={() => setSelectedSpaceId(space.id)}
              >
                {space.name}
              </Button>
            ))}
          </div>
        )}

        {selectedSpaceId && (
          <div className="rounded-lg border bg-card p-4 flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-semibold mb-2">
                {t("reservations.booking.existingBookings")}
              </h2>
              {sortedSpaceReservations.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {t("reservations.booking.noBookings")}
                </p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {sortedSpaceReservations.map((res) => (
                    <li
                      key={res.id}
                      className="flex items-center justify-between text-sm border-b py-1.5 last:border-b-0"
                    >
                      <span>
                        {new Date(res.start_time).toLocaleString()} –{" "}
                        {new Date(res.end_time).toLocaleString()}
                        {res.reserved_by_id
                          ? ` (${res.reserved_by_name ?? ""})`
                          : ` (${t("reservations.booking.masked")})`}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass(res.status)}`}
                      >
                        {res.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {!isGuest && (
              <form onSubmit={handleCreate} className="flex flex-col gap-3">
                <p className="text-sm font-semibold">
                  {t("reservations.booking.newBooking")}
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium mb-1">
                      {t("reservations.booking.startTime")}
                    </label>
                    <input
                      type="datetime-local"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1">
                      {t("reservations.booking.endTime")}
                    </label>
                    <input
                      type="datetime-local"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("reservations.booking.notesPlaceholder")}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={2}
                />
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!startTime || !endTime || createMutation.isPending}
                  >
                    {t("reservations.booking.submit")}
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

      {!isGuest && (
        <div>
          <h2 className="text-lg font-bold mb-3">
            {t("reservations.booking.myReservations")}
          </h2>
          {(myReservations ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("reservations.booking.noMyReservations")}
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {(myReservations ?? []).map((res) => (
                <li
                  key={res.id}
                  className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
                >
                  <div className="flex flex-col gap-0.5 text-sm">
                    <span className="font-medium">{res.space_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(res.start_time).toLocaleString()} –{" "}
                      {new Date(res.end_time).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass(res.status)}`}
                    >
                      {res.status}
                    </span>
                    {canCancelClientSide(res) && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleCancel(res.id)}
                        disabled={cancelMutation.isPending}
                      >
                        {t("reservations.booking.cancel")}
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {isStaff && (
        <div>
          <h2 className="text-lg font-bold mb-3">
            {t("reservations.booking.pendingApprovals")}
          </h2>
          {pendingList.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("reservations.booking.noPendingApprovals")}
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {pendingList.map((res) => (
                <li
                  key={res.id}
                  className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
                >
                  <div className="flex flex-col gap-0.5 text-sm">
                    <span className="font-medium">
                      {res.space_name} — {res.reserved_by_name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(res.start_time).toLocaleString()} –{" "}
                      {new Date(res.end_time).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReject(res.id)}
                      disabled={rejectMutation.isPending}
                    >
                      {t("reservations.booking.reject")}
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleApprove(res.id)}
                      disabled={approveMutation.isPending}
                    >
                      {t("reservations.booking.approve")}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default SpaceBookingPage;
