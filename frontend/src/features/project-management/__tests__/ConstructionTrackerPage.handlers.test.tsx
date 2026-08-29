import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConstructionTrackerPage } from '../components/ConstructionTrackerPage';
import * as projectsApi from '../../../api/projects';
import type {
  ConstructionProject,
  PaginatedProjects,
  ProjectDetail,
  ProjectMilestone,
  ProjectUpdate,
} from '../../../types/project';

vi.mock('../../../api/projects');

const mockEffectiveIdentity = vi.fn();
vi.mock('../../user-administration/context/useEffectiveIdentity', () => ({
  useEffectiveIdentity: () => mockEffectiveIdentity(),
}));

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
  cover_photo_url: null,
  created_at: '2026-08-20T10:00:00Z',
  updated_at: '2026-08-20T10:00:00Z',
};

const mockMilestone: ProjectMilestone = {
  id: 'm-1',
  project_id: 'proj-1',
  title: 'Demolição do piso antigo',
  description: 'Remoção do piso antigo',
  status: 'DONE',
  due_date: '2026-09-05',
  completion_date: '2026-09-04',
  display_order: 1,
  created_at: '2026-08-20T10:00:00Z',
  updated_at: '2026-08-20T10:00:00Z',
};

const mockUpdate: ProjectUpdate = {
  id: 'up-1',
  project_id: 'proj-1',
  author_id: 'user-admin',
  author: {
    id: 'user-admin',
    full_name: 'Engenheiro Carlos',
    email: 'carlos@obra.com',
  },
  title: 'Primeira demão aplicada',
  content: 'Piso devidamente lixado e selado.',
  photos: [],
  cost_impact: null,
  created_at: '2026-09-10T14:30:00Z',
};

const mockProjectsResponse: PaginatedProjects = {
  items: [mockProject],
  total: 1,
  skip: 0,
  limit: 50,
};

const mockProjectDetail: ProjectDetail = {
  ...mockProject,
  milestones: [mockMilestone],
  updates: [mockUpdate],
};

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

/** Opens the detail view of the single seeded project. */
const openProjectDetail = async () => {
  fireEvent.click(await screen.findByText('Ver Detalhes'));
  await screen.findByText('Voltar para Lista de Obras');
};

describe('ConstructionTrackerPage handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEffectiveIdentity.mockReturnValue({
      role: 'ADMINISTRATOR',
      userTypeIds: [],
      isSimulating: false,
    });
    vi.mocked(projectsApi.getProjects).mockResolvedValue(mockProjectsResponse);
    vi.mocked(projectsApi.getProjectDetail).mockResolvedValue(mockProjectDetail);
    vi.mocked(projectsApi.createProject).mockResolvedValue(mockProject);
    vi.mocked(projectsApi.updateProject).mockResolvedValue(mockProject);
    vi.mocked(projectsApi.deleteProject).mockResolvedValue(undefined);
    vi.mocked(projectsApi.createMilestone).mockResolvedValue(mockMilestone);
    vi.mocked(projectsApi.updateMilestone).mockResolvedValue(mockMilestone);
    vi.mocked(projectsApi.deleteMilestone).mockResolvedValue(undefined);
    vi.mocked(projectsApi.createProjectUpdate).mockResolvedValue(mockUpdate);
    vi.mocked(projectsApi.deleteProjectUpdate).mockResolvedValue(undefined);
  });

  describe('handleSaveProject', () => {
    it('creates a project when no project is being edited', async () => {
      renderPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Nova Obra' }));
      fireEvent.change(screen.getByLabelText(/Título da Obra/i), {
        target: { value: 'Nova Guarita' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

      await waitFor(() =>
        expect(projectsApi.createProject).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Nova Guarita', status: 'PLANNED' })
        )
      );
      expect(projectsApi.updateProject).not.toHaveBeenCalled();
    });

    it('updates the edited project instead of creating a new one', async () => {
      renderPage();

      fireEvent.click(await screen.findByLabelText('edit-project'));
      fireEvent.change(screen.getByLabelText(/Título da Obra/i), {
        target: { value: 'Reforma da Quadra II' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

      await waitFor(() =>
        expect(projectsApi.updateProject).toHaveBeenCalledWith(
          'proj-1',
          expect.objectContaining({
            title: 'Reforma da Quadra II',
            contractor_name: 'Alfa Construtora',
          })
        )
      );
      expect(projectsApi.createProject).not.toHaveBeenCalled();
    });
  });

  describe('handleConfirmDeleteProject', () => {
    it('deletes the project confirmed from the list card', async () => {
      renderPage();

      fireEvent.click(await screen.findByLabelText('delete-project'));
      fireEvent.click(
        await screen.findByRole('button', { name: 'Excluir Obra' })
      );

      await waitFor(() =>
        expect(projectsApi.deleteProject).toHaveBeenCalledWith('proj-1')
      );
    });

    it('deletes the open project and returns to the list view', async () => {
      renderPage();
      await openProjectDetail();

      fireEvent.click(screen.getByRole('button', { name: 'Excluir' }));
      fireEvent.click(
        await screen.findByRole('button', { name: 'Excluir Obra' })
      );

      await waitFor(() =>
        expect(projectsApi.deleteProject).toHaveBeenCalledWith('proj-1')
      );
      await waitFor(() =>
        expect(screen.queryByText('Voltar para Lista de Obras')).toBeNull()
      );
    });
  });

  describe('handleSaveMilestone', () => {
    it('creates a milestone under the selected project', async () => {
      renderPage();
      await openProjectDetail();

      fireEvent.click(screen.getByText('Novo Marco'));
      fireEvent.change(screen.getByLabelText(/Título do Marco/i), {
        target: { value: 'Fundação' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Salvar Marco' }));

      await waitFor(() =>
        expect(projectsApi.createMilestone).toHaveBeenCalledWith(
          'proj-1',
          expect.objectContaining({ title: 'Fundação' })
        )
      );
      expect(projectsApi.updateMilestone).not.toHaveBeenCalled();
    });

    it('updates the edited milestone of the selected project', async () => {
      renderPage();
      await openProjectDetail();

      fireEvent.click(screen.getByLabelText('edit-milestone'));
      fireEvent.change(screen.getByLabelText(/Título do Marco/i), {
        target: { value: 'Demolição concluída' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Salvar Marco' }));

      await waitFor(() =>
        expect(projectsApi.updateMilestone).toHaveBeenCalledWith(
          'proj-1',
          'm-1',
          expect.objectContaining({ title: 'Demolição concluída' })
        )
      );
      expect(projectsApi.createMilestone).not.toHaveBeenCalled();
    });
  });

  it('deletes the confirmed milestone of the selected project', async () => {
    renderPage();
    await openProjectDetail();

    fireEvent.click(screen.getByLabelText('delete-milestone'));
    fireEvent.click(
      await screen.findByRole('button', { name: 'Excluir Marco' })
    );

    await waitFor(() =>
      expect(projectsApi.deleteMilestone).toHaveBeenCalledWith('proj-1', 'm-1')
    );
  });

  it('publishes a project update for the selected project', async () => {
    renderPage();
    await openProjectDetail();

    // The feed's "add" control and the modal's submit share the same label;
    // the feed button is the only one on screen before the modal opens.
    fireEvent.click(
      screen.getByRole('button', { name: 'Publicar Atualização' })
    );
    fireEvent.change(screen.getByLabelText(/Título da Atualização/i), {
      target: { value: 'Materiais Entregues' },
    });
    fireEvent.change(screen.getByLabelText(/Relato das Atividades/i), {
      target: { value: 'Cimento e areia descarregados' },
    });

    const submitButtons = screen.getAllByRole('button', {
      name: 'Publicar Atualização',
    });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() =>
      expect(projectsApi.createProjectUpdate).toHaveBeenCalledWith(
        'proj-1',
        expect.objectContaining({
          title: 'Materiais Entregues',
          content: 'Cimento e areia descarregados',
        })
      )
    );
  });

  it('deletes the confirmed update of the selected project', async () => {
    renderPage();
    await openProjectDetail();

    fireEvent.click(screen.getByLabelText('delete-update'));

    // The detail toolbar also carries an "Excluir" button; the confirmation
    // one is rendered last, inside the alert modal.
    const confirmButtons = await screen.findAllByRole('button', {
      name: 'Excluir',
    });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() =>
      expect(projectsApi.deleteProjectUpdate).toHaveBeenCalledWith(
        'proj-1',
        'up-1'
      )
    );
  });

  it('refetches with the chosen status filter and shows the empty state', async () => {
    renderPage();
    await screen.findByText('Reforma da Quadra');

    vi.mocked(projectsApi.getProjects).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 50,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Concluída' }));

    await waitFor(() =>
      expect(projectsApi.getProjects).toHaveBeenCalledWith({
        status: 'COMPLETED',
      })
    );
    expect(
      await screen.findByText('Nenhuma obra cadastrada')
    ).toBeInTheDocument();
  });

  it('refetches the list from the refresh control', async () => {
    renderPage();
    await screen.findByText('Reforma da Quadra');
    const callsBefore = vi.mocked(projectsApi.getProjects).mock.calls.length;

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar' }));

    await waitFor(() =>
      expect(
        vi.mocked(projectsApi.getProjects).mock.calls.length
      ).toBeGreaterThan(callsBefore)
    );
  });

  it('hides every create/edit/delete control from a non-managing role', async () => {
    mockEffectiveIdentity.mockReturnValue({
      role: 'RESIDENT',
      userTypeIds: [],
      isSimulating: false,
    });
    renderPage();
    await screen.findByText('Reforma da Quadra');

    expect(screen.queryByRole('button', { name: 'Nova Obra' })).toBeNull();
    expect(screen.queryByLabelText('edit-project')).toBeNull();
    expect(screen.queryByLabelText('delete-project')).toBeNull();

    await openProjectDetail();

    expect(screen.queryByRole('button', { name: 'Editar Obra' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Excluir' })).toBeNull();
    expect(screen.queryByText('Novo Marco')).toBeNull();
    expect(screen.queryByLabelText('edit-milestone')).toBeNull();
    expect(screen.queryByLabelText('delete-milestone')).toBeNull();
    expect(screen.queryByLabelText('delete-update')).toBeNull();
    expect(
      screen.queryByRole('button', { name: 'Publicar Atualização' })
    ).toBeNull();
  });
});
