import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { TaskPriority, TaskStatus } from "../types";
import type { TaskRead, TaskCreate, TaskUpdate } from "../types";
import {
  useAuth,
  UserRole,
} from "../../user-administration/context/AuthContext";
import { useCreateTask, useUpdateTask } from "../hooks/useTasks";
import { useCategories } from "../hooks/useCategories";
import { useAssignableUsers } from "../../../hooks/useUsers";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { Select } from "../../../components/ui/select";
import { Label } from "../../../components/ui/label";
import { Alert, AlertDescription } from "../../../components/ui/alert";
import { getStatusLabel } from "../utils/taskUtils";

interface TaskFormProps {
  task?: TaskRead;
  onSuccess: () => void;
  onCancel: () => void;
}

const TaskForm: React.FC<TaskFormProps> = ({ task, onSuccess, onCancel }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isEditing = !!task;
  const createTaskMutation = useCreateTask();
  const updateTaskMutation = useUpdateTask();
  const { data: users } = useAssignableUsers();
  const { data: categories } = useCategories();

  const { data: userTypes } = useUserTypes();

  const isLoading =
    createTaskMutation.isPending || updateTaskMutation.isPending;
  const serverError = createTaskMutation.error || updateTaskMutation.error;

  const defaultValues = {
    title: "",
    description: "",
    priority: TaskPriority.MEDIUM,
    assigned_to_id: "",
    due_date: "",
    status: TaskStatus.PENDING,
    category_id: "",
    visible_to_id: "",
  };

  const transforms: Record<string, (value: unknown) => unknown> = {
    title: (v) => v,
    description: (v) => v || "",
    priority: (v) => v,
    assigned_to_id: (v) => v || "",
    due_date: (v) =>
      v ? new Date(v as string).toISOString().split("T")[0] : "",
    status: (v) => v,
    category_id: (v) => v || "",
    visible_to_id: (v) => v || "",
  };

  const getInitialState = () => {
    const initial: Record<string, unknown> = {};
    (Object.keys(defaultValues) as Array<keyof typeof defaultValues>).forEach(
      (key) => {
        const value = task ? task[key as keyof TaskRead] : defaultValues[key];
        initial[key] = transforms[key](value);
      },
    );
    return initial;
  };

  const [formData, setFormData] = useState(getInitialState());
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!(formData.title as string).trim())
      newErrors.title = t("tasks.form.titleRequired");
    if (!(formData.category_id as string))
      newErrors.category_id = t("tasks.form.categoryRequired");
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const commonData: TaskCreate = {
      title: formData.title as string,
      description: (formData.description as string) || null,
      priority: formData.priority as TaskPriority,
      due_date: formData.due_date
        ? new Date(formData.due_date as string)
        : null,
      assigned_to_id: (formData.assigned_to_id as string) || null,
      category_id: formData.category_id as string,
      visible_to_id: (formData.visible_to_id as string) || null,
    };

    if (isEditing && task) {
      const updatePayload: TaskUpdate = {
        ...commonData,
        status: formData.status as TaskStatus,
        visible_to_id: (formData.visible_to_id as string) || null,
      };
      updateTaskMutation.mutate(
        { id: task.id, data: updatePayload },
        { onSuccess },
      );
    } else {
      createTaskMutation.mutate(commonData, { onSuccess });
    }
  };

  let submitText = t("tasks.form.submitCreate");
  if (isLoading) {
    submitText = t("tasks.form.submitSaving");
  } else if (isEditing) {
    submitText = t("tasks.form.submitEdit");
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-foreground mb-5">
        {isEditing ? t("tasks.form.editTitle") : t("tasks.form.newTitle")}
      </h2>

      {serverError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            {(serverError as { response?: { data?: { detail?: string } } })
              .response?.data?.detail || t("tasks.form.errorSaving")}
          </AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="title">{t("tasks.form.titleLabel")}</Label>
          <Input
            id="title"
            name="title"
            value={formData.title as string}
            onChange={handleChange}
            disabled={isLoading}
            placeholder={t("tasks.form.titlePlaceholder")}
            aria-invalid={Boolean(errors.title)}
          />
          {errors.title && (
            <p className="text-xs text-destructive">{errors.title}</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="description">
            {t("tasks.form.descriptionLabel")}
          </Label>
          <Textarea
            id="description"
            name="description"
            value={formData.description as string}
            onChange={handleChange}
            disabled={isLoading}
            placeholder={t("tasks.form.descriptionPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="priority">{t("tasks.form.priorityLabel")}</Label>
          <Select
            id="priority"
            name="priority"
            value={formData.priority as string}
            onChange={handleChange}
            disabled={isLoading}
          >
            {Object.values(TaskPriority).map((p) => (
              <option key={p} value={p}>
                {t(`tasks.priority.${p}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="category_id">{t("tasks.form.categoryLabel")}</Label>
          <Select
            id="category_id"
            name="category_id"
            value={formData.category_id as string}
            onChange={handleChange}
            disabled={isLoading}
            aria-invalid={Boolean(errors.category_id)}
          >
            <option value=""></option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </Select>
          {errors.category_id && (
            <p className="text-xs text-destructive">{errors.category_id}</p>
          )}
        </div>

        {isEditing && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="status">{t("tasks.form.statusLabel")}</Label>
            <Select
              id="status"
              name="status"
              value={formData.status as string}
              onChange={handleChange}
              disabled={isLoading}
            >
              {Object.values(TaskStatus).map((s) => (
                <option key={s} value={s}>
                  {getStatusLabel(s, t)}
                </option>
              ))}
            </Select>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="assigned_to_id">
            {t("tasks.form.assigneeLabel")}
          </Label>
          <Select
            id="assigned_to_id"
            name="assigned_to_id"
            value={formData.assigned_to_id as string}
            onChange={handleChange}
            disabled={isLoading}
          >
            <option value="">{t("tasks.form.unassigned")}</option>
            {users?.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name || user.email}
              </option>
            ))}
          </Select>
          <p className="text-xs text-muted-foreground">
            {t("tasks.form.assigneeHelper")}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="due_date">{t("tasks.form.dueDateLabel")}</Label>
          <Input
            type="date"
            id="due_date"
            name="due_date"
            value={formData.due_date as string}
            onChange={handleChange}
            disabled={isLoading}
          />
        </div>

        {user?.role !== UserRole.MANAGER && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="visible_to_id">{t("tasks.form.visibleToLabel")}</Label>
            <Select
              id="visible_to_id"
              name="visible_to_id"
              value={formData.visible_to_id as string}
              onChange={handleChange}
              disabled={isLoading}
            >
              <option value="">{t("tasks.form.visibleToAll")}</option>
              {userTypes?.map((ut) => (
                <option key={ut.id} value={ut.id}>
                  {ut.name}
                </option>
              ))}
            </Select>
            <p className="text-xs text-muted-foreground">
              {t("tasks.form.visibleToHelper")}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2 border-t">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
          >
            {t("tasks.form.cancel")}
          </Button>
          <Button type="submit" disabled={isLoading}>
            {submitText}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default TaskForm;
