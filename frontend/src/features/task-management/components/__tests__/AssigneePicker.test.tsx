import React from "react";
import {
  render,
  screen,
  fireEvent,
  within,
  waitFor,
} from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AssigneePicker from "../AssigneePicker";
import type { User } from "../../../../types/auth";

const users: User[] = [
  {
    id: "user-1",
    email: "marta@apras.test",
    full_name: "Marta Nogueira",
    is_active: true,
    roles: [{ id: "r1", name: "Síndica" }],
  },
  {
    id: "user-2",
    email: "marcos@apras.test",
    full_name: "Marcos Caldeira",
    is_active: true,
    roles: [{ id: "r2", name: "Zelador" }],
  },
  {
    id: "user-3",
    email: "ana@apras.test",
    full_name: "Ana Marques",
    is_active: true,
    roles: [],
  },
  {
    id: "user-4",
    email: "helio@apras.test",
    full_name: "Helio Braga",
    is_active: true,
    roles: [{ id: "r3", name: "Conselheiro" }],
  },
];

const renderPicker = (
  props: Partial<React.ComponentProps<typeof AssigneePicker>> = {},
) =>
  render(
    <AssigneePicker
      id="assigned_to_id"
      users={users}
      value={null}
      onChange={vi.fn()}
      {...props}
    />,
  );

const openListbox = () => {
  fireEvent.focus(screen.getByRole("combobox"));
  return screen.getByRole("listbox");
};

describe("AssigneePicker", () => {
  it("shows the selected person's name when closed", () => {
    renderPicker({ value: "user-1" });
    expect(screen.getByRole("combobox")).toHaveValue("Marta Nogueira");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows every person plus the explicit no-assignee option", () => {
    renderPicker();
    const listbox = openListbox();
    const options = within(listbox).getAllByRole("option");
    expect(options).toHaveLength(5);
    expect(options[4]).toHaveTextContent("Deixar sem responsável");
  });

  it("renders initials, name and role for each person", () => {
    renderPicker();
    const listbox = openListbox();
    const option = within(listbox).getAllByRole("option")[0];
    expect(option).toHaveTextContent("MN");
    expect(option).toHaveTextContent("Marta Nogueira");
    expect(option).toHaveTextContent("Síndica");
  });

  it("names the absence of a role rather than leaving the line blank", () => {
    renderPicker();
    const listbox = openListbox();
    expect(within(listbox).getAllByRole("option")[2]).toHaveTextContent(
      "Sem papel",
    );
  });

  it("narrows the options as the name is typed", () => {
    renderPicker();
    openListbox();
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "marc" },
    });
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Marcos Caldeira");
  });

  it("matches case- and accent-insensitively, and on the email", () => {
    renderPicker();
    openListbox();
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "MARCOS" },
    });
    expect(screen.getAllByRole("option")[0]).toHaveTextContent(
      "Marcos Caldeira",
    );

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "hélio" },
    });
    expect(screen.getAllByRole("option")[0]).toHaveTextContent("Helio Braga");

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "ana@apras" },
    });
    expect(screen.getAllByRole("option")[0]).toHaveTextContent("Ana Marques");
  });

  it("reports when nothing matches", () => {
    renderPicker();
    openListbox();
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "zzzz" },
    });
    expect(screen.getByText("Nenhuma pessoa encontrada")).toBeInTheDocument();
  });

  it("selects a person by click and closes", () => {
    const onChange = vi.fn();
    renderPicker({ onChange });
    openListbox();

    fireEvent.click(screen.getAllByRole("option")[1]);
    expect(onChange).toHaveBeenCalledWith("user-2");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("clears the assignee through the explicit option", () => {
    const onChange = vi.fn();
    renderPicker({ value: "user-1", onChange });
    openListbox();

    fireEvent.click(
      screen.getByRole("option", { name: /Deixar sem responsável/ }),
    );
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("is navigable with the arrow keys and Enter", () => {
    const onChange = vi.fn();
    renderPicker({ onChange });
    const input = screen.getByRole("combobox");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("user-2");
  });

  it("wraps around with ArrowUp from the first option", () => {
    const onChange = vi.fn();
    renderPicker({ onChange });
    const input = screen.getByRole("combobox");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("marks the active option as selected", () => {
    renderPicker();
    fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
    expect(screen.getAllByRole("option")[0]).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("closes on Escape and restores the selected name", () => {
    renderPicker({ value: "user-1" });
    const input = screen.getByRole("combobox");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "marc" } });
    fireEvent.keyDown(input, { key: "Escape" });

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(input).toHaveValue("Marta Nogueira");
  });

  it("ignores Enter while closed", () => {
    const onChange = vi.fn();
    renderPicker({ onChange });
    fireEvent.keyDown(screen.getByRole("combobox"), { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("reports whether the listbox is open", () => {
    renderPicker();
    const input = screen.getByRole("combobox");
    expect(input).toHaveAttribute("aria-expanded", "false");
    fireEvent.focus(input);
    expect(input).toHaveAttribute("aria-expanded", "true");
  });

  it("cannot be opened while disabled", () => {
    renderPicker({ disabled: true });
    const input = screen.getByRole("combobox");
    expect(input).toBeDisabled();
    fireEvent.focus(input);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("tolerates an empty user list", () => {
    renderPicker({ users: [] });
    const listbox = openListbox();
    expect(within(listbox).getAllByRole("option")).toHaveLength(1);
  });

  it("wraps past the last option back to the first", () => {
    renderPicker();
    const input = screen.getByRole("combobox");

    // Five options: four people plus "leave unassigned".
    for (let i = 0; i < 6; i += 1) {
      fireEvent.keyDown(input, { key: "ArrowDown" });
    }
    expect(screen.getAllByRole("option")[0]).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("follows the mouse, and keeps the input focused on press", () => {
    renderPicker();
    const listbox = openListbox();
    const options = within(listbox).getAllByRole("option");

    fireEvent.mouseEnter(options[1]);
    expect(options[1]).toHaveAttribute("aria-selected", "true");

    fireEvent.mouseEnter(options[4]);
    expect(options[4]).toHaveAttribute("aria-selected", "true");

    // The listbox must not steal focus, or the blur would close it first.
    const pressed = fireEvent.mouseDown(options[1]);
    expect(pressed).toBe(false);
  });

  it("closes when the field loses focus", async () => {
    renderPicker();
    const input = screen.getByRole("combobox");
    fireEvent.focus(input);
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    fireEvent.blur(input);
    await waitFor(() =>
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument(),
    );
  });
});
