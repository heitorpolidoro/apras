import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import UserTypeMultiSelect from "../components/UserTypeMultiSelect";

const userTypes = [
  { id: "type-1", name: "Board Member" },
  { id: "type-2", name: "Building Staff" },
];

describe("UserTypeMultiSelect", () => {
  it("shows a placeholder when nothing is selected", () => {
    render(
      <UserTypeMultiSelect userTypes={userTypes} selectedIds={[]} onChange={vi.fn()} />,
    );
    expect(screen.getByText("Selecionar tipos de usuário")).toBeInTheDocument();
  });

  it("shows a badge for each selected UserType", () => {
    render(
      <UserTypeMultiSelect
        userTypes={userTypes}
        selectedIds={["type-1"]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Board Member")).toBeInTheDocument();
    expect(screen.queryByText("Building Staff")).not.toBeInTheDocument();
  });

  it("opens the checkbox list when the trigger button is clicked", () => {
    render(
      <UserTypeMultiSelect userTypes={userTypes} selectedIds={[]} onChange={vi.fn()} />,
    );
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("calls onChange adding the id when an unselected UserType is checked", () => {
    const onChange = vi.fn();
    render(
      <UserTypeMultiSelect userTypes={userTypes} selectedIds={[]} onChange={onChange} />,
    );
    fireEvent.click(screen.getByRole("button"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(onChange).toHaveBeenCalledWith(["type-1"]);
  });

  it("calls onChange removing the id when a selected UserType is unchecked", () => {
    const onChange = vi.fn();
    render(
      <UserTypeMultiSelect
        userTypes={userTypes}
        selectedIds={["type-1", "type-2"]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(onChange).toHaveBeenCalledWith(["type-2"]);
  });

  it("shows an empty-state message when there are no UserTypes available", () => {
    render(<UserTypeMultiSelect userTypes={[]} selectedIds={[]} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(
      screen.getByText("Nenhum tipo de usuário disponível."),
    ).toBeInTheDocument();
  });

  it("closes the list when clicking outside the component", () => {
    render(
      <div>
        <UserTypeMultiSelect userTypes={userTypes} selectedIds={[]} onChange={vi.fn()} />
        <button>Outside</button>
      </div>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Selecionar tipos/i }));
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByText("Outside"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
