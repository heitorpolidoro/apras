import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import RoleMultiSelect from "../components/RoleMultiSelect";

const roles = [
  { id: "type-1", name: "Board Member" },
  { id: "type-2", name: "Building Staff" },
];

describe("RoleMultiSelect", () => {
  it("shows a placeholder when nothing is selected", () => {
    render(
      <RoleMultiSelect roles={roles} selectedIds={[]} onChange={vi.fn()} />,
    );
    expect(screen.getByText("Selecionar papéis")).toBeInTheDocument();
  });

  it("shows a badge for each selected Role", () => {
    render(
      <RoleMultiSelect
        roles={roles}
        selectedIds={["type-1"]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Board Member")).toBeInTheDocument();
    expect(screen.queryByText("Building Staff")).not.toBeInTheDocument();
  });

  it("opens the checkbox list when the trigger button is clicked", () => {
    render(
      <RoleMultiSelect roles={roles} selectedIds={[]} onChange={vi.fn()} />,
    );
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("calls onChange adding the id when an unselected Role is checked", () => {
    const onChange = vi.fn();
    render(
      <RoleMultiSelect roles={roles} selectedIds={[]} onChange={onChange} />,
    );
    fireEvent.click(screen.getByRole("button"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(onChange).toHaveBeenCalledWith(["type-1"]);
  });

  it("calls onChange removing the id when a selected Role is unchecked", () => {
    const onChange = vi.fn();
    render(
      <RoleMultiSelect
        roles={roles}
        selectedIds={["type-1", "type-2"]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(onChange).toHaveBeenCalledWith(["type-2"]);
  });

  it("shows an empty-state message when there are no Roles available", () => {
    render(<RoleMultiSelect roles={[]} selectedIds={[]} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(
      screen.getByText("Nenhum papel disponível."),
    ).toBeInTheDocument();
  });

  it("closes the list when clicking outside the component", () => {
    render(
      <div>
        <RoleMultiSelect roles={roles} selectedIds={[]} onChange={vi.fn()} />
        <button>Outside</button>
      </div>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Selecionar papéis/i }));
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByText("Outside"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
