import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { useTranslation } from "react-i18next";
import TaskComments from "../TaskComments";
import { useComments, useCreateComment, useUpdateComment,  } from "../../hooks/useTasks";
import { useAuth } from "../../../user-administration/context/AuthContext";

vi.mock("../../hooks/useTasks", () => ({
  useComments: vi.fn(),
  useCreateComment: vi.fn(),
  useUpdateComment: vi.fn(),
}));

vi.mock("../../../user-administration/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

/** Typed mock helper for useAuth. */
const mockAuth = (userId: string) =>
  vi
    .mocked(useAuth)
    .mockReturnValue({ user: { id: userId } } as unknown as ReturnType<
      typeof useAuth
    >);

/** Typed mock helper for useComments. */
const mockComments = (
  data: ReturnType<typeof useComments>["data"],
  isLoading = false,
) =>
  vi
    .mocked(useComments)
    .mockReturnValue({ data, isLoading } as unknown as ReturnType<
      typeof useComments
    >);

/** Typed mock helper for useCreateComment. */
const mockCreateComment = (
  mutate: ReturnType<typeof useCreateComment>["mutate"],
  isPending = false,
) =>
  vi
    .mocked(useCreateComment)
    .mockReturnValue({ mutate, isPending } as unknown as ReturnType<
      typeof useCreateComment
    >);

/** Typed mock helper for useUpdateComment. */
const mockUpdateComment = (
  mutate: ReturnType<typeof useUpdateComment>["mutate"],
  isPending = false,
) =>
  vi
    .mocked(useUpdateComment)
    .mockReturnValue({ mutate, isPending } as unknown as ReturnType<
      typeof useUpdateComment
    >);

const baseComment = {
  id: "comment-1",
  task_id: "task-1",
  created_by_id: "user-1",
  created_by_name: "Alice",
  content: "This is a comment",
  created_at: "2023-01-01T10:00:00Z",
  updated_at: "2023-01-01T10:00:00Z",
};

describe("TaskComments", () => {
  const mockCreateMutate = vi.fn();
  const mockUpdateMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth("user-1");
    mockComments([baseComment]);
    mockCreateComment(mockCreateMutate);
    mockUpdateComment(mockUpdateMutate);
  });

  it("renders the comments section title", () => {
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText(/Comentários/i)).toBeInTheDocument();
  });

  it("renders existing comments", () => {
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText("This is a comment")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockComments(undefined, true);
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText(/Carregando comentários/i)).toBeInTheDocument();
  });

  it("shows empty state when no comments", () => {
    mockComments([]);
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText(/Nenhum comentário ainda/i)).toBeInTheDocument();
  });

  it("submits a new comment", () => {
    render(<TaskComments taskId="task-1" />);

    const textarea = screen.getByPlaceholderText(/Escreva um comentário/i);
    fireEvent.change(textarea, { target: { value: "New comment" } });

    fireEvent.click(screen.getByRole("button", { name: /Comentar/i }));

    expect(mockCreateMutate).toHaveBeenCalledWith(
      "New comment",
      expect.any(Object),
    );
  });

  it("disables send button when textarea is empty", () => {
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByRole("button", { name: /Comentar/i })).toBeDisabled();
  });

  it("shows sending state while creating", () => {
    mockCreateComment(mockCreateMutate, true);
    render(<TaskComments taskId="task-1" />);
    expect(
      screen.getByRole("button", { name: /Enviando/i }),
    ).toBeInTheDocument();
  });

  it("shows edit button only for comment owner", () => {
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
  });

  it("does not show edit button for other users' comments", () => {
    mockAuth("other-user");
    render(<TaskComments taskId="task-1" />);
    expect(
      screen.queryByRole("button", { name: /editar/i }),
    ).not.toBeInTheDocument();
  });

  it("enters edit mode when edit button is clicked", () => {
    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    expect(screen.getByRole("button", { name: /Salvar/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Cancelar/i }),
    ).toBeInTheDocument();
  });

  it("saves edited comment", () => {
    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    const editTextarea = screen.getAllByRole("textbox")[0];
    fireEvent.change(editTextarea, { target: { value: "Updated comment" } });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        commentId: "comment-1",
        content: "Updated comment",
      }),
      expect.any(Object),
    );
  });

  it("cancels edit and restores original content", () => {
    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    const editTextarea = screen.getAllByRole("textbox")[0];
    fireEvent.change(editTextarea, { target: { value: "Changed text" } });
    fireEvent.click(screen.getByRole("button", { name: /Cancelar/i }));

    expect(screen.getByText("This is a comment")).toBeInTheDocument();
    expect(mockUpdateMutate).not.toHaveBeenCalled();
  });

  it("does not call mutate when saving unchanged content", () => {
    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mockUpdateMutate).not.toHaveBeenCalled();
  });

  it("shows (editado) marker when updated_at differs from created_at", () => {
    mockComments([{ ...baseComment, updated_at: "2023-01-02T12:00:00Z" }]);
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText(/editado/i)).toBeInTheDocument();
  });

  it("disables save/cancel buttons when update is pending", () => {
    mockUpdateComment(mockUpdateMutate, true);
    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    expect(screen.getByRole("button", { name: /Salvar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Cancelar/i })).toBeDisabled();
  });

  it("exits edit mode after successful update", async () => {
    mockUpdateComment(((_payload: unknown, opts: { onSuccess: () => void }) => {
      opts.onSuccess();
    }) as ReturnType<typeof useUpdateComment>["mutate"]);

    render(<TaskComments taskId="task-1" />);

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    const editTextarea = screen.getAllByRole("textbox")[0];
    fireEvent.change(editTextarea, { target: { value: "Updated content" } });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Salvar/i })).not.toBeInTheDocument();
    });
  });

  it("clears textarea after successful comment submission", async () => {
    mockCreateComment(((_content: unknown, opts: { onSuccess: () => void }) => {
      opts.onSuccess();
    }) as ReturnType<typeof useCreateComment>["mutate"]);

    render(<TaskComments taskId="task-1" />);

    const textarea = screen.getByPlaceholderText(/Escreva um comentário/i);
    fireEvent.change(textarea, { target: { value: "My comment" } });
    fireEvent.click(screen.getByRole("button", { name: /Comentar/i }));

    await waitFor(() => {
      expect(textarea).toHaveValue("");
    });
  });

  it("handles undefined user from useAuth", () => {
    vi.mocked(useAuth).mockReturnValue({ user: undefined } as any); // skipcq: JS-0323
    render(<TaskComments taskId="task-1" />);
    expect(screen.getByText("This is a comment")).toBeInTheDocument();
  });

  it("does not submit empty comment", () => {
    render(<TaskComments taskId="task-1" />);
    const textarea = screen.getByPlaceholderText(/Escreva um comentário/i);
    const form = textarea.closest("form") as HTMLFormElement;
    fireEvent.submit(form);
    expect(mockCreateMutate).not.toHaveBeenCalled();
  });

  it("formats date in English locale when language is not pt", () => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => s,
      i18n: { language: "en", changeLanguage: vi.fn() },
    } as any); // skipcq: JS-0323

    const toLocaleStringSpy = vi.spyOn(Date.prototype, "toLocaleString");

    render(<TaskComments taskId="task-1" />);

    expect(toLocaleStringSpy).toHaveBeenCalledWith("en-US");
    toLocaleStringSpy.mockRestore();
  });
});
