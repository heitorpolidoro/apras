import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QrScannerModal } from "../components/QrScannerModal";
import { Html5Qrcode } from "html5-qrcode";

const mockStart = vi.fn();
const mockStop = vi.fn();
const mockClear = vi.fn();

vi.mock("html5-qrcode", () => ({
  Html5Qrcode: vi.fn().mockImplementation(function MockHtml5Qrcode(this: any) {
    this.start = mockStart;
    this.stop = mockStop;
    this.clear = mockClear;
  }),
}));

describe("QrScannerModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStart.mockResolvedValue(null);
    mockStop.mockResolvedValue(undefined);
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <QrScannerModal isOpen={false} onClose={vi.fn()} onScanSuccess={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
    expect(Html5Qrcode).not.toHaveBeenCalled();
  });

  it("starts the camera scanner when opened", async () => {
    render(<QrScannerModal isOpen={true} onClose={vi.fn()} onScanSuccess={vi.fn()} />);

    await waitFor(() => expect(mockStart).toHaveBeenCalledTimes(1));
    expect(Html5Qrcode).toHaveBeenCalledTimes(1);
  });

  it("invokes onScanSuccess with the decoded text when the camera reads a code", async () => {
    const onScanSuccess = vi.fn();
    render(<QrScannerModal isOpen={true} onClose={vi.fn()} onScanSuccess={onScanSuccess} />);

    await waitFor(() => expect(mockStart).toHaveBeenCalledTimes(1));

    const successCallback = mockStart.mock.calls[0][2];
    successCallback("11111111-1111-1111-1111-111111111111");

    expect(onScanSuccess).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111");
  });

  it("stops the scanner on unmount", async () => {
    const { unmount } = render(
      <QrScannerModal isOpen={true} onClose={vi.fn()} onScanSuccess={vi.fn()} />
    );

    await waitFor(() => expect(mockStart).toHaveBeenCalledTimes(1));

    unmount();

    await waitFor(() => expect(mockStop).toHaveBeenCalledTimes(1));
  });
});
