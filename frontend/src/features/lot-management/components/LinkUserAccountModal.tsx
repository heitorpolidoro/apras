import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Search } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useUsers } from "../../../hooks/useUsers";
import type { ResidentDetail } from "../../../types/resident";

interface LinkUserAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  resident: ResidentDetail | null;
  onLink: (residentId: string, userId: string) => Promise<void>;
  isLoading?: boolean;
}

export const LinkUserAccountModal: React.FC<LinkUserAccountModalProps> = ({
  isOpen,
  onClose,
  resident,
  onLink,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const { data: users = [], isLoading: isUsersLoading } = useUsers();

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !resident) return null;

  const filteredUsers = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!selectedUserId) {
      setErrorMsg(t("residents.selectUserRequired"));
      return;
    }

    try {
      await onLink(resident.id, selectedUserId);
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || t("residents.linkError");
      setErrorMsg(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        <h3 className="text-lg font-bold text-foreground mb-2">
          {t("residents.linkUserModalTitle")}
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          {t("residents.linkUserModalSubtitle", { name: resident.full_name })}
        </p>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t("residents.searchUserPlaceholder")}
              className="w-full rounded-md border border-input pl-9 pr-3 py-2 text-sm bg-card text-foreground"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              {t("residents.selectUserAccount")}
            </label>
            {isUsersLoading ? (
              <p className="text-xs text-muted-foreground p-2">{t("residents.loadingUsers")}</p>
            ) : filteredUsers.length === 0 ? (
              <p className="text-xs text-muted-foreground p-2">{t("residents.noUsersFound")}</p>
            ) : (
              <div className="max-h-48 overflow-y-auto rounded-md border border-border divide-y divide-slate-100 dark:divide-slate-800">
                {filteredUsers.map((user) => (
                  <label
                    key={user.id}
                    className={`flex items-center space-x-3 px-3 py-2 text-xs cursor-pointer hover:bg-accent ${
                      selectedUserId === user.id ? "bg-emerald-50 dark:bg-emerald-950/40" : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="user-account"
                      value={user.id}
                      checked={selectedUserId === user.id}
                      onChange={() => setSelectedUserId(user.id)}
                      className="text-primary focus:ring-ring"
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-foreground">
                        {user.full_name}
                      </div>
                      <div className="text-muted-foreground text-[11px]">{user.email}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end space-x-3">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              {t("residents.cancel")}
            </Button>
            <Button type="submit" size="sm" disabled={isLoading || !selectedUserId}>
              {isLoading ? t("residents.linking") : t("residents.linkAccount")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
