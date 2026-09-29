import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConstructionTrackerPage } from '../components/ConstructionTrackerPage';
import { ProjectSummaryCard } from '../components/ProjectSummaryCard';
import * as projectsApi from '../../../api/projects';
import {
  UPLOAD_ACCEPT,
  UPLOAD_MAX_FILE_SIZE_BYTES,
} from '../../../api/uploads';
import type {
  ConstructionProject,
  PaginatedProjects,
  ProjectDetail,
} from '../../../types/project';

import { PERMISSIONS_BY_ROLE } from '../../../test/permissionFixtures';

/**
 * The obra cover photo, chosen as a file rather than pasted as a URL
 * (APRAS-104 ER1).
 *
 * Two things are under test here and they are deliberately separate:
 *
 * * the **control**: the URL textbox is gone, a picked `File` is held in form
 *   state and uploaded through `PUT /projects/{id}/cover-photo` after the obra
 *   is saved, and a file the browser can refuse locally never reaches the
 *   network;
 * * the **create sequence** (§B), which is not cosmetic. If the create
 *   succeeded and only the cover upload failed, a modal still in create mode
 *   would answer the operator's natural next action -- press Save again -- with
 *   a second `POST /projects`, i.e. a duplicate obra. So the modal adopts the
 *   returned id and switches to editing it *before* the cover step runs.
 *
 * And the card reads `cover_photo_display_url`, never `cover_photo_url`: the
 * stored column is storage truth in a Blob store configured with **private**
 * access, so an `<img src>` pointed at it loads nothing at all.
 */

const hasOf = (profile: string) => (permission: string) =>
  (PERMISSIONS_BY_ROLE[profile] ?? []).includes(permission);

vi.mock('../../../api/projects');

const mockPermissionSet = vi.fn();
vi.mock('../../user-administration/access/useCanAccess', () => ({
  useEffectivePermissionSet: () => mockPermissionSet(),
}));

const DISPLAY_URL =
  'https://apras-back.vercel.app/api/v1/public/tenants/aprasvi/projects/proj-1/cover';

const mockProject: ConstructionProject = {
  id: 'proj-1',
  title: 'Reforma da Quadra',
  description: 'Pintura epóxi e iluminação',
  contractor_name: 'Alfa Construtora',
  total_budget: 100000,
  executed_budget: 45000,
  physical_progress_pct: 45,
  start_date: '2026-09-01',
  estimated_completion_date: '2026-12-01',
  actual_completion_date: null,
  status: 'IN_PROGRESS',
  cover_photo_url: '/static/uploads/2026/09/abc.png',
  cover_photo_display_url: DISPLAY_URL,
  created_at: '2026-08-20T10:00:00Z',
  updated_at: '2026-08-20T10:00:00Z',
};

const mockProjectsResponse: PaginatedProjects = {
  items: [mockProject],
  total: 1,
  skip: 0,
  limit: 50,
};

const mockProjectDetail: ProjectDetail = {
  ...mockProject,
  milestones: [],
  updates: [],
};

/** A real `File`, so "that file's bytes" is a value and not a shape. */
const pngFile = (name = 'capa.png') =>
  new File([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10])], name, {
    type: 'image/png',
  });

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConstructionTrackerPage />
    </QueryClientProvider>
  );
};

const coverInput = () =>
  document.querySelector<HTMLInputElement>('input[type="file"]')!;

describe('the obra cover photo is chosen as a file', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissionSet.mockReturnValue({ has: hasOf('ADMINISTRATOR') });
    vi.mocked(projectsApi.getProjects).mockResolvedValue(mockProjectsResponse);
    vi.mocked(projectsApi.getProjectDetail).mockResolvedValue(mockProjectDetail);
    vi.mocked(projectsApi.createProject).mockResolvedValue(mockProject);
    vi.mocked(projectsApi.updateProject).mockResolvedValue(mockProject);
    vi.mocked(projectsApi.putProjectCoverPhoto).mockResolvedValue(mockProject);
    vi.mocked(projectsApi.deleteProjectCoverPhoto).mockResolvedValue(
      mockProject
    );
  });

  // -------------------------------------------------------------------------
  // ER1 -- the control
  // -------------------------------------------------------------------------

  it('uploads the picked file for that obra and sends no cover_photo_url', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));

    // The URL field is gone. Asserted by its old label, which is the thing an
    // operator would recognise and the thing a regression would restore.
    expect(
      screen.queryByLabelText(/URL da Foto de Capa/i)
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /URL/i })).toBeNull();

    const file = pngFile();
    fireEvent.change(coverInput(), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

    await waitFor(() =>
      expect(projectsApi.putProjectCoverPhoto).toHaveBeenCalledWith(
        'proj-1',
        file
      )
    );

    // The project payload carries **no** `cover_photo_url` key at all -- not
    // `null`, absent. `ProjectService.update_project` skips `None`, so a `null`
    // would be silently dropped and the assertion would prove nothing about
    // the form having stopped sending it.
    const [, payload] = vi.mocked(projectsApi.updateProject).mock.calls[0];
    expect(payload).not.toHaveProperty('cover_photo_url');
  });

  it('issues no cover request when nothing was picked', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));
    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

    await waitFor(() => expect(projectsApi.updateProject).toHaveBeenCalled());
    expect(projectsApi.putProjectCoverPhoto).not.toHaveBeenCalled();
    expect(projectsApi.deleteProjectCoverPhoto).not.toHaveBeenCalled();
  });

  it('removes the cover through the DELETE route when Remover is pressed', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));
    fireEvent.click(screen.getByRole('button', { name: /Remover/i }));
    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

    await waitFor(() =>
      expect(projectsApi.deleteProjectCoverPhoto).toHaveBeenCalledWith('proj-1')
    );
    expect(projectsApi.putProjectCoverPhoto).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // ER1 -- the two local refusals, which never reach the network
  // -------------------------------------------------------------------------

  it('refuses a non-image locally, naming the accepted formats', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));
    fireEvent.change(coverInput(), {
      target: {
        files: [new File(['nao sou imagem'], 'notas.txt', { type: 'text/plain' })],
      },
    });

    expect(await screen.findByText(/JPEG, PNG, WebP/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));
    await waitFor(() => expect(projectsApi.updateProject).toHaveBeenCalled());
    // Refused in the browser, so it never reached the network.
    expect(projectsApi.putProjectCoverPhoto).not.toHaveBeenCalled();
  });

  it('refuses an oversized file locally, naming the 5MB limit', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));
    // Pinned against the shared constant, never a retyped literal: it is the
    // frontend half of the two-sided pin `api/uploads.ts` declares against
    // `media_service.MAX_FILE_SIZE`.
    const oversized = pngFile('enorme.png');
    Object.defineProperty(oversized, 'size', {
      value: UPLOAD_MAX_FILE_SIZE_BYTES + 1,
    });
    fireEvent.change(coverInput(), { target: { files: [oversized] } });

    expect(await screen.findByText(/5MB/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));
    await waitFor(() => expect(projectsApi.updateProject).toHaveBeenCalled());
    expect(projectsApi.putProjectCoverPhoto).not.toHaveBeenCalled();
  });

  it('accepts exactly the three types the backend accepts', async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText('edit-project'));

    expect(coverInput().accept).toBe(UPLOAD_ACCEPT);
    expect(UPLOAD_ACCEPT).toBe('image/jpeg,image/png,image/webp');
  });

  // -------------------------------------------------------------------------
  // ER1 -- the create sequence: one create, never two
  // -------------------------------------------------------------------------

  it('never issues a second create when the cover upload fails', async () => {
    vi.mocked(projectsApi.putProjectCoverPhoto).mockRejectedValue(
      new Error('a rede recusou o envio')
    );
    // The created obra as the server really answers it: with the title that was
    // typed. Adopting it remounts the form on the saved obra, so the form then
    // shows the server's values rather than stale local ones -- which is the
    // point, and which a mock echoing a different title would hide.
    vi.mocked(projectsApi.createProject).mockResolvedValue({
      ...mockProject,
      title: 'Nova Guarita',
      cover_photo_display_url: null,
      cover_photo_url: null,
    });
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Nova Obra' }));
    fireEvent.change(screen.getByLabelText(/Título da Obra/i), {
      target: { value: 'Nova Guarita' },
    });
    fireEvent.change(coverInput(), { target: { files: [pngFile()] } });
    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

    // Exactly one create, and the cover error is displayed rather than
    // swallowed.
    await waitFor(() =>
      expect(projectsApi.createProject).toHaveBeenCalledTimes(1)
    );
    expect(
      await screen.findByText(/foto de capa não foi enviada/i)
    ).toBeInTheDocument();
    // The modal is still open on that obra.
    expect(screen.getByLabelText(/Título da Obra/i)).toBeInTheDocument();

    // Pressing Save again re-issues a PUT, never a second POST. That is the
    // whole point of adopting the created id before the cover step runs.
    vi.mocked(projectsApi.putProjectCoverPhoto).mockResolvedValue(mockProject);
    fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

    await waitFor(() =>
      expect(projectsApi.updateProject).toHaveBeenCalledWith(
        'proj-1',
        expect.objectContaining({ title: 'Nova Guarita' })
      )
    );
    expect(projectsApi.createProject).toHaveBeenCalledTimes(1);
  });

  // -------------------------------------------------------------------------
  // The card's two branches
  // -------------------------------------------------------------------------

  it('the card loads the derived display URL, never the stored column', () => {
    render(
      <ProjectSummaryCard
        project={mockProject}
        onSelect={vi.fn()}
        canManage={false}
      />
    );

    const image = screen.getByAltText('Reforma da Quadra') as HTMLImageElement;
    expect(image.getAttribute('src')).toBe(DISPLAY_URL);
    // The stored value is a private Blob object: an `<img src>` pointed at it
    // loads nothing, so it must not appear.
    expect(image.getAttribute('src')).not.toBe(mockProject.cover_photo_url);
    expect(document.body.innerHTML).not.toContain('/static/uploads/2026/09/abc.png');
  });

  it('the card keeps its placeholder when there is no display URL', () => {
    render(
      <ProjectSummaryCard
        project={{
          ...mockProject,
          cover_photo_display_url: null,
          // Present and non-null on purpose: a card that still read the column
          // would render an image here and fail this case.
          cover_photo_url: '/static/uploads/2026/09/abc.png',
        }}
        onSelect={vi.fn()}
        canManage={false}
      />
    );

    expect(screen.getByText('Sem foto de capa')).toBeInTheDocument();
    expect(screen.queryByAltText('Reforma da Quadra')).toBeNull();
  });
});
