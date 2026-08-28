import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import {
  useAssemblies,
  useCloseAssembly,
  useCloseVote,
  useCreateAssembly,
  useCreateVote,
  useEligibleLots,
  useUpdateAssembly,
  useVotes,
} from "../hooks/useVoting";
import AssemblyMinutesView from "./AssemblyMinutesView";
import LotVotingAdminPanel from "./LotVotingAdminPanel";
import VoteBallotCard from "./VoteBallotCard";
import VoteTallyPanel from "./VoteTallyPanel";
import type { AssemblyType, VoteKind, VoteRead } from "../../../types/voting";

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

const emptyOptions = ["", ""];

/**
 * Assemblies and polls.
 *
 * Board roles (ADMINISTRATOR/DIRECTOR) drive the assembly lifecycle;
 * MANAGER may only open polls. Whether the caller can actually cast a
 * ballot is decided by the API, not here.
 */
const AssemblyVotingPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const isBoard =
    role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;
  const canCreatePoll = isBoard || role === UserRole.MANAGER;

  const [kind, setKind] = useState<VoteKind>("ASSEMBLEIA");
  const [selectedAssemblyId, setSelectedAssemblyId] = useState<string | null>(
    null,
  );
  const [selectedVoteId, setSelectedVoteId] = useState<string | null>(null);
  const [showAssemblyForm, setShowAssemblyForm] = useState(false);
  const [showVoteForm, setShowVoteForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [assemblyTitle, setAssemblyTitle] = useState("");
  const [assemblyType, setAssemblyType] = useState<AssemblyType>("AGO");
  const [heldOn, setHeldOn] = useState("");
  const [agenda, setAgenda] = useState("");

  const [voteTitle, setVoteTitle] = useState("");
  const [voteDescription, setVoteDescription] = useState("");
  const [voteType, setVoteType] = useState<"SINGLE_CHOICE" | "MULTIPLE_CHOICE">(
    "SINGLE_CHOICE",
  );
  const [closesAt, setClosesAt] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [optionLabels, setOptionLabels] = useState<string[]>(emptyOptions);

  const { data: assemblies, isLoading: assembliesLoading } = useAssemblies();
  const { data: votes, isLoading: votesLoading } = useVotes(
    kind === "ASSEMBLEIA"
      ? { kind: "ASSEMBLEIA", assembly_id: selectedAssemblyId ?? undefined }
      : { kind: "ENQUETE" },
  );
  const { data: eligibleLots } = useEligibleLots(selectedVoteId ?? undefined);

  const createAssemblyMutation = useCreateAssembly();
  const closeAssemblyMutation = useCloseAssembly();
  const updateAssemblyMutation = useUpdateAssembly();
  const createVoteMutation = useCreateVote();
  const closeVoteMutation = useCloseVote();

  const selectedAssembly = useMemo(
    () => assemblies?.find((item) => item.id === selectedAssemblyId) ?? null,
    [assemblies, selectedAssemblyId],
  );
  const selectedVote: VoteRead | null = useMemo(
    () => votes?.find((item) => item.id === selectedVoteId) ?? null,
    [votes, selectedVoteId],
  );

  const handleCreateAssembly = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    createAssemblyMutation.mutate(
      {
        title: assemblyTitle,
        type: assemblyType,
        held_on: heldOn,
        agenda: agenda.trim() || null,
      },
      {
        onSuccess: () => {
          setShowAssemblyForm(false);
          setAssemblyTitle("");
          setAgenda("");
          setHeldOn("");
        },
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail ||
              t("voting.assemblies.errorCreating"),
          ),
      },
    );
  };

  const handleCreateVote = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    createVoteMutation.mutate(
      {
        assembly_id: kind === "ASSEMBLEIA" ? selectedAssemblyId : null,
        kind,
        title: voteTitle,
        description: voteDescription.trim() || null,
        vote_type: voteType,
        is_anonymous: kind === "ENQUETE" ? isAnonymous : false,
        closes_at: closesAt ? new Date(closesAt).toISOString() : "",
        options: optionLabels
          .filter((label) => label.trim())
          .map((label, index) => ({ label: label.trim(), order_index: index })),
      },
      {
        onSuccess: () => {
          setShowVoteForm(false);
          setVoteTitle("");
          setVoteDescription("");
          setClosesAt("");
          setOptionLabels(emptyOptions);
        },
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail || t("voting.votes.errorCreating"),
          ),
      },
    );
  };

  const handleCloseAssembly = (assemblyId: string) => {
    setError(null);
    closeAssemblyMutation.mutate(assemblyId, {
      onError: (err: ApiError) =>
        setError(
          err.response?.data?.detail || t("voting.assemblies.errorClosing"),
        ),
    });
  };

  /**
   * Release a DRAFT agenda. Until the assembly is OPEN the API refuses
   * every ballot with VoteNotOpenError, so this is what actually starts
   * the voting.
   */
  const handleOpenAssembly = (assemblyId: string) => {
    setError(null);
    updateAssemblyMutation.mutate(
      { id: assemblyId, data: { status: "OPEN" } },
      {
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail || t("voting.assemblies.errorOpening"),
          ),
      },
    );
  };

  const handleCloseVote = (voteId: string) => {
    setError(null);
    closeVoteMutation.mutate(voteId, {
      onError: (err: ApiError) =>
        setError(err.response?.data?.detail || t("voting.votes.errorClosing")),
    });
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-black">{t("voting.title")}</h1>
        <div className="flex gap-2">
          <Button
            type="button"
            variant={kind === "ASSEMBLEIA" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setKind("ASSEMBLEIA");
              setSelectedVoteId(null);
            }}
          >
            {t("voting.kind.ASSEMBLEIA")}
          </Button>
          <Button
            type="button"
            variant={kind === "ENQUETE" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setKind("ENQUETE");
              setSelectedVoteId(null);
              setSelectedAssemblyId(null);
            }}
          >
            {t("voting.kind.ENQUETE")}
          </Button>
        </div>
      </header>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {kind === "ASSEMBLEIA" && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">{t("voting.assemblies.title")}</h2>
            {isBoard && (
              <Button
                type="button"
                size="sm"
                onClick={() => setShowAssemblyForm((value) => !value)}
              >
                {t("voting.assemblies.new")}
              </Button>
            )}
          </div>

          {showAssemblyForm && (
            <form onSubmit={handleCreateAssembly} className="space-y-2">
              <Input
                value={assemblyTitle}
                onChange={(event) => setAssemblyTitle(event.target.value)}
                placeholder={t("voting.assemblies.titleLabel")}
                aria-label={t("voting.assemblies.titleLabel")}
              />
              <select
                aria-label={t("voting.assemblies.type")}
                className="rounded-md border border-border/60 px-2 py-1 text-sm"
                value={assemblyType}
                onChange={(event) =>
                  setAssemblyType(event.target.value as AssemblyType)
                }
              >
                <option value="AGO">{t("voting.assemblies.typeAGO")}</option>
                <option value="AGE">{t("voting.assemblies.typeAGE")}</option>
              </select>
              <Input
                type="date"
                value={heldOn}
                onChange={(event) => setHeldOn(event.target.value)}
                aria-label={t("voting.assemblies.heldOn")}
              />
              <Textarea
                value={agenda}
                onChange={(event) => setAgenda(event.target.value)}
                placeholder={t("voting.assemblies.agenda")}
                aria-label={t("voting.assemblies.agenda")}
              />
              <Button type="submit" size="sm">
                {t("voting.assemblies.create")}
              </Button>
            </form>
          )}

          {assembliesLoading && (
            <p className="text-sm text-muted-foreground">
              {t("voting.assemblies.loading")}
            </p>
          )}

          {!assembliesLoading && (assemblies?.length ?? 0) === 0 && (
            <p className="text-sm text-muted-foreground">
              {t("voting.assemblies.empty")}
            </p>
          )}

          <ul className="space-y-2">
            {assemblies?.map((assembly) => (
              <li
                key={assembly.id}
                className="rounded-md border border-border/60 p-3 flex items-center justify-between gap-2"
              >
                <button
                  type="button"
                  className="text-left"
                  onClick={() => {
                    setSelectedAssemblyId(assembly.id);
                    setSelectedVoteId(null);
                  }}
                >
                  <span className="font-semibold">{assembly.title}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {assembly.type} ·{" "}
                    {t(`voting.assemblies.status.${assembly.status}`)}
                  </span>
                </button>
                <div className="flex items-center gap-2">
                  {isBoard && assembly.status === "DRAFT" && (
                    <>
                      <span className="text-xs text-muted-foreground">
                        {t("voting.assemblies.openHint")}
                      </span>
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => handleOpenAssembly(assembly.id)}
                      >
                        {t("voting.assemblies.openAction")}
                      </Button>
                    </>
                  )}
                  {isBoard && assembly.status !== "CLOSED" && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleCloseAssembly(assembly.id)}
                    >
                      {t("voting.assemblies.close")}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {selectedAssembly && (
            <AssemblyMinutesView assembly={selectedAssembly} />
          )}
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">{t("voting.votes.title")}</h2>
          {((kind === "ASSEMBLEIA" && isBoard && selectedAssemblyId) ||
            (kind === "ENQUETE" && canCreatePoll)) && (
            <Button
              type="button"
              size="sm"
              onClick={() => setShowVoteForm((value) => !value)}
            >
              {kind === "ASSEMBLEIA"
                ? t("voting.votes.newAssemblyVote")
                : t("voting.votes.newPoll")}
            </Button>
          )}
        </div>

        {showVoteForm && (
          <form onSubmit={handleCreateVote} className="space-y-2">
            <Input
              value={voteTitle}
              onChange={(event) => setVoteTitle(event.target.value)}
              placeholder={t("voting.votes.titleLabel")}
              aria-label={t("voting.votes.titleLabel")}
            />
            <Textarea
              value={voteDescription}
              onChange={(event) => setVoteDescription(event.target.value)}
              placeholder={t("voting.votes.description")}
              aria-label={t("voting.votes.description")}
            />
            <select
              aria-label={t("voting.votes.voteType")}
              className="rounded-md border border-border/60 px-2 py-1 text-sm"
              value={voteType}
              onChange={(event) =>
                setVoteType(
                  event.target.value as "SINGLE_CHOICE" | "MULTIPLE_CHOICE",
                )
              }
            >
              <option value="SINGLE_CHOICE">
                {t("voting.votes.singleChoice")}
              </option>
              <option value="MULTIPLE_CHOICE">
                {t("voting.votes.multipleChoice")}
              </option>
            </select>
            <Input
              type="datetime-local"
              value={closesAt}
              onChange={(event) => setClosesAt(event.target.value)}
              aria-label={t("voting.votes.closesAt")}
            />
            {kind === "ENQUETE" && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={isAnonymous}
                  onChange={(event) => setIsAnonymous(event.target.checked)}
                />
                {t("voting.votes.anonymous")}
              </label>
            )}
            {isAnonymous && kind === "ENQUETE" && (
              <p className="text-xs text-muted-foreground">
                {t("voting.anonymityNotice")}
              </p>
            )}
            <div className="space-y-1">
              {optionLabels.map((label, index) => (
                <Input
                  key={`option-${index}`}
                  value={label}
                  onChange={(event) =>
                    setOptionLabels((current) =>
                      current.map((item, position) =>
                        position === index ? event.target.value : item,
                      ),
                    )
                  }
                  placeholder={t("voting.votes.optionPlaceholder")}
                  aria-label={`${t("voting.votes.optionPlaceholder")} ${index + 1}`}
                />
              ))}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setOptionLabels((current) => [...current, ""])}
              >
                {t("voting.votes.addOption")}
              </Button>
            </div>
            <Button type="submit" size="sm">
              {t("voting.votes.create")}
            </Button>
          </form>
        )}

        {votesLoading && (
          <p className="text-sm text-muted-foreground">
            {t("voting.votes.loading")}
          </p>
        )}

        {!votesLoading && (votes?.length ?? 0) === 0 && (
          <p className="text-sm text-muted-foreground">
            {t("voting.votes.empty")}
          </p>
        )}

        <ul className="space-y-2">
          {votes?.map((vote) => (
            <li
              key={vote.id}
              className="rounded-md border border-border/60 p-3 flex items-center justify-between gap-2"
            >
              <button
                type="button"
                className="text-left"
                onClick={() => setSelectedVoteId(vote.id)}
              >
                <span className="font-semibold">{vote.title}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {t(`voting.voteStatus.${vote.status}`)}
                </span>
              </button>
              {canCreatePoll && vote.status === "OPEN" && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleCloseVote(vote.id)}
                >
                  {t("voting.votes.close")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </section>

      {canCreatePoll && <LotVotingAdminPanel />}

      {selectedVote && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold">{selectedVote.title}</h2>
          <VoteBallotCard
            vote={selectedVote}
            eligibleLots={eligibleLots ?? []}
          />
          <VoteTallyPanel vote={selectedVote} />
        </div>
      )}
    </div>
  );
};

export default AssemblyVotingPage;
