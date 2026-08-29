import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AssetSummaryCards } from "../components/AssetSummaryCards";

describe("AssetSummaryCards component", () => {
  it("renders metric cards with formatted values", () => {
    const summary = {
      total_assets: 15,
      total_consumables: 42,
      low_stock_count: 3,
      total_patrimonial_value: 12500.5,
    };

    render(<AssetSummaryCards summary={summary} />);

    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/12\.500,50/)).toBeInTheDocument();
  });

  it("renders loading state", () => {
    render(<AssetSummaryCards isLoading={true} />);
    const placeholders = screen.getAllByText("...");
    expect(placeholders.length).toBe(4);
  });
});
