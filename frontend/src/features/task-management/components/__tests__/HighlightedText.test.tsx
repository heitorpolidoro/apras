import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HighlightedText from "../HighlightedText";

describe("HighlightedText", () => {
  it("wraps the matched fragment in a mark", () => {
    const { container } = render(
      <HighlightedText text="Revisão da manutenção do elevador" search="manutencao" />,
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("manutenção");
    expect(container.textContent).toBe("Revisão da manutenção do elevador");
  });

  it("highlights every occurrence", () => {
    const { container } = render(
      <HighlightedText text="Ata da ata" search="ata" />,
    );
    expect(container.querySelectorAll("mark")).toHaveLength(2);
  });

  it("renders plain text when the search is blank", () => {
    const { container } = render(
      <HighlightedText text="Trocar lâmpadas" search="   " />,
    );
    expect(container.querySelectorAll("mark")).toHaveLength(0);
    expect(screen.getByText("Trocar lâmpadas")).toBeInTheDocument();
  });

  it("renders plain text when the search is absent", () => {
    const { container } = render(<HighlightedText text="Trocar lâmpadas" />);
    expect(container.querySelectorAll("mark")).toHaveLength(0);
  });

  it("renders plain text when nothing matches", () => {
    const { container } = render(
      <HighlightedText text="Trocar lâmpadas" search="piscina" />,
    );
    expect(container.querySelectorAll("mark")).toHaveLength(0);
    expect(container.textContent).toBe("Trocar lâmpadas");
  });

  it("renders nothing for an empty text", () => {
    const { container } = render(<HighlightedText text="" search="a" />);
    expect(container.textContent).toBe("");
  });
});
