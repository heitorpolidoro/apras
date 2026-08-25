import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AvatarWithFallback from '../components/AvatarWithFallback';
import PhotoUploadModal from '../components/PhotoUploadModal';
import AvatarCropEditor from '../components/AvatarCropEditor';
import WebcamCaptureDialog from '../components/WebcamCaptureDialog';
import PhotoApprovalQueuePage from '../components/PhotoApprovalQueuePage';
import { MediaAssetRead } from '../../../types/media_asset';
import * as uploadsApi from '../../../api/uploads';

vi.mock('../../../api/uploads', () => ({
  uploadPhoto: vi.fn(),
  getPendingPhotos: vi.fn(),
  approvePhoto: vi.fn(),
  rejectPhoto: vi.fn(),
  deletePhoto: vi.fn(),
  getPhotoMetadata: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => options?.defaultValue || key,
    i18n: { changeLanguage: () => Promise.resolve() },
  }),
}));

const mockMediaAsset: MediaAssetRead = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  entity_type: 'RESIDENT',
  entity_id: '98765432-e89b-12d3-a456-426614174000',
  storage_provider: 'LOCAL_DISK',
  file_path: 'static/uploads/2026/08/test.jpg',
  url: '/static/uploads/2026/08/test.jpg',
  thumbnail_url: '/static/uploads/2026/08/thumb_test.jpg',
  file_size_bytes: 1024,
  mime_type: 'image/jpeg',
  width: 300,
  height: 300,
  status: 'PENDING_APPROVAL',
  rejection_reason: null,
  uploaded_by_id: 'user-111',
  uploaded_by_name: 'John Resident',
  created_at: '2026-08-25T10:00:00Z',
  updated_at: '2026-08-25T10:00:00Z',
};

describe('Media Asset Components & Workflow', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  describe('AvatarWithFallback Component', () => {
    it('renders fallback initials when photo is missing or pending', () => {
      render(<AvatarWithFallback name="Carlos Silva" photoUrl={null} status="PENDING_APPROVAL" />);
      expect(screen.getByText('CS')).toBeInTheDocument();
      expect(screen.getByText('Em Aprovação')).toBeInTheDocument();
    });

    it('renders image avatar when photo is APPROVED', () => {
      render(
        <AvatarWithFallback
          name="Carlos Silva"
          photoUrl="/static/uploads/photo.jpg"
          status="APPROVED"
        />
      );
      const img = screen.getByRole('img');
      expect(img).toHaveAttribute('src', '/static/uploads/photo.jpg');
    });
  });

  describe('AvatarCropEditor Component', () => {
    it('renders canvas and controls for image cropping', () => {
      const mockOnCrop = vi.fn();
      render(
        <AvatarCropEditor
          imageSrc="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
          onCropComplete={mockOnCrop}
          onCancel={vi.fn()}
        />
      );
      expect(screen.getByText('Ajustar Recorte da Foto')).toBeInTheDocument();
      expect(screen.getByText('Confirmar Recorte')).toBeInTheDocument();
    });
  });

  describe('WebcamCaptureDialog Component', () => {
    it('renders webcam capture modal controls', () => {
      render(
        <WebcamCaptureDialog
          isOpen={true}
          onClose={vi.fn()}
          onCapture={vi.fn()}
        />
      );
      expect(screen.getByText('Capturar Foto da Câmera')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Capturar Foto/i })).toBeInTheDocument();
    });
  });

  describe('PhotoUploadModal Component', () => {
    it('allows file selection and triggers upload', async () => {
      vi.mocked(uploadsApi.uploadPhoto).mockResolvedValue(mockMediaAsset);

      const handleSuccess = vi.fn();
      render(
        <QueryClientProvider client={queryClient}>
          <PhotoUploadModal
            isOpen={true}
            onClose={vi.fn()}
            onSuccess={handleSuccess}
            entityType="RESIDENT"
            entityId="98765432-e89b-12d3-a456-426614174000"
          />
        </QueryClientProvider>
      );

      expect(screen.getByText('Enviar Foto de Cadastro')).toBeInTheDocument();
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['fake-image'], 'test.png', { type: 'image/png' });

      fireEvent.change(fileInput, { target: { files: [file] } });

      await waitFor(() => {
        expect(screen.getByText('Enviar Foto')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Enviar Foto'));

      await waitFor(() => {
        expect(uploadsApi.uploadPhoto).toHaveBeenCalled();
        expect(handleSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('PhotoApprovalQueuePage Component', () => {
    it('fetches and displays pending photo approvals list', async () => {
      vi.mocked(uploadsApi.getPendingPhotos).mockResolvedValue({
        items: [mockMediaAsset],
        total: 1,
        pending_count: 1,
      });

      render(
        <QueryClientProvider client={queryClient}>
          <PhotoApprovalQueuePage />
        </QueryClientProvider>
      );

      expect(screen.getByText('Fila de Aprovação de Fotos')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('John Resident')).toBeInTheDocument();
      });
    });

    it('handles photo approval action', async () => {
      vi.mocked(uploadsApi.getPendingPhotos).mockResolvedValue({
        items: [mockMediaAsset],
        total: 1,
        pending_count: 1,
      });
      vi.mocked(uploadsApi.approvePhoto).mockResolvedValue({
        ...mockMediaAsset,
        status: 'APPROVED',
      });

      render(
        <QueryClientProvider client={queryClient}>
          <PhotoApprovalQueuePage />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('John Resident')).toBeInTheDocument();
      });

      const approveBtn = screen.getByRole('button', { name: /Aprovar/i });
      fireEvent.click(approveBtn);

      await waitFor(() => {
        expect(uploadsApi.approvePhoto).toHaveBeenCalledWith(mockMediaAsset.id);
      });
    });

    it('handles photo rejection with reason dialog', async () => {
      vi.mocked(uploadsApi.getPendingPhotos).mockResolvedValue({
        items: [mockMediaAsset],
        total: 1,
        pending_count: 1,
      });
      vi.mocked(uploadsApi.rejectPhoto).mockResolvedValue({
        ...mockMediaAsset,
        status: 'REJECTED',
        rejection_reason: 'Foto escura',
      });

      render(
        <QueryClientProvider client={queryClient}>
          <PhotoApprovalQueuePage />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('John Resident')).toBeInTheDocument();
      });

      const rejectBtn = screen.getByRole('button', { name: /Rejeitar/i });
      fireEvent.click(rejectBtn);

      expect(screen.getByText('Motivo da Rejeição')).toBeInTheDocument();

      const reasonInput = screen.getByPlaceholderText(/Informe o motivo/i);
      fireEvent.change(reasonInput, { target: { value: 'Foto escura' } });

      const confirmRejectBtn = screen.getByRole('button', { name: /Confirmar Rejeição/i });
      fireEvent.click(confirmRejectBtn);

      await waitFor(() => {
        expect(uploadsApi.rejectPhoto).toHaveBeenCalledWith(mockMediaAsset.id, 'Foto escura');
      });
    });
  });
});
