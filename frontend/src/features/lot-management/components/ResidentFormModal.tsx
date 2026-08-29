import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import {
  type ResidentCreatePayload,
  type ResidentDetail,
  ResidentRelationship,
  type ResidentUpdatePayload,
} from "../../../types/resident";

interface ResidentFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ResidentCreatePayload | ResidentUpdatePayload) => Promise<void>;
  initialData?: ResidentDetail | null;
  isLoading?: boolean;
}

export const ResidentFormModal: React.FC<ResidentFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading = false,
}) => {
  const { t } = useTranslation();

  const [fullName, setFullName] = useState("");
  const [cpf, setCpf] = useState("");
  const [rg, setRg] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [relationshipType, setRelationshipType] = useState<ResidentRelationship>(
    ResidentRelationship.TITULAR
  );
  const [notes, setNotes] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setFullName(initialData.full_name || "");
      setCpf(initialData.cpf || "");
      setRg(initialData.rg || "");
      setBirthDate(initialData.birth_date || "");
      setPhone(initialData.phone || "");
      setEmail(initialData.email || "");
      setRelationshipType(initialData.relationship_type || ResidentRelationship.TITULAR);
      setNotes(initialData.notes || "");
    } else {
      setFullName("");
      setCpf("");
      setRg("");
      setBirthDate("");
      setPhone("");
      setEmail("");
      setRelationshipType(ResidentRelationship.TITULAR);
      setNotes("");
    }
    setErrorMsg(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!fullName.trim()) {
      setErrorMsg(t("residents.validationNameRequired"));
      return;
    }
    if (!cpf.trim()) {
      setErrorMsg(t("residents.validationCpfRequired"));
      return;
    }

    try {
      await onSubmit({
        full_name: fullName.trim(),
        cpf: cpf.trim(),
        rg: rg.trim() || undefined,
        birth_date: birthDate || undefined,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
        relationship_type: relationshipType,
        notes: notes.trim() || undefined,
      });
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || t("residents.saveError");
      setErrorMsg(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
          {initialData ? t("residents.editResident") : t("residents.newResident")}
        </h3>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              {t("residents.name")} *
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              placeholder={t("residents.namePlaceholder")}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                CPF *
              </label>
              <input
                type="text"
                required
                value={cpf}
                onChange={(e) => setCpf(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                placeholder="000.000.000-00"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                RG
              </label>
              <input
                type="text"
                value={rg}
                onChange={(e) => setRg(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                placeholder="00.000.000-0"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {t("residents.birthDate")}
              </label>
              <input
                type="date"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {t("residents.relationship")} *
              </label>
              <select
                value={relationshipType}
                onChange={(e) => setRelationshipType(e.target.value as ResidentRelationship)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value={ResidentRelationship.TITULAR}>{t("residents.relTitular")}</option>
                <option value={ResidentRelationship.CONJUGE}>{t("residents.relConjuge")}</option>
                <option value={ResidentRelationship.FILHO_DEPENDENTE}>{t("residents.relFilho")}</option>
                <option value={ResidentRelationship.INQUILINO}>{t("residents.relInquilino")}</option>
                <option value={ResidentRelationship.PARENTE}>{t("residents.relParente")}</option>
                <option value={ResidentRelationship.OUTRO}>{t("residents.relOutro")}</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {t("residents.phone")}
              </label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                placeholder="(00) 00000-0000"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                E-mail
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                placeholder="nome@email.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              {t("residents.notes")}
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              placeholder={t("residents.notesPlaceholder")}
            />
          </div>

          <div className="mt-6 flex justify-end space-x-3">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              {t("residents.cancel")}
            </Button>
            <Button type="submit" size="sm" disabled={isLoading}>
              {isLoading ? t("residents.saving") : t("residents.save")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
