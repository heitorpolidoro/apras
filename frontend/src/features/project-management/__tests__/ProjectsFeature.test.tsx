import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BudgetVsActualProgressBar } from '../components/BudgetVsActualProgressBar';
import { MilestoneTimeline } from '../components/MilestoneTimeline';
import { ProjectUpdateFeed } from '../components/ProjectUpdateFeed';
import { ProjectSummaryCard } from '../components/ProjectSummaryCard';
import { ProjectFormModal } from '../components/ProjectFormModal';
import { MilestoneFormModal } from '../components/MilestoneFormModal';
import { ProjectUpdateModal } from '../components/ProjectUpdateModal';
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

const mockProject1: ConstructionProject = {
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
  cover_photo_url: 'https://example.com/cover.jpg',
  created_at: '2026-08-20T10:00:00Z',
  updated_at: '2026-08-20T10:00:00Z',
};

const mockProject2: ConstructionProject = {
  id: 'proj-2',
  title: 'Pintura Fachada',
  description: 'Pintura externa',
  contractor_name: 'Beta Tintas',
  total_budget: 50000,
  executed_budget: 55000, // Over budget
  physical_progress_pct: 100,
  start_date: '2026-06-01',
  estimated_completion_date: '2026-08-01',
  actual_completion_date: '2026-08-15',
  status: 'COMPLETED',
  cover_photo_url: null,
  created_at: '2026-08-15T10:00:00Z',
  updated_at: '2026-08-15T10:00:00Z',
};

const mockProjectsResponse: PaginatedProjects = {
  items: [mockProject1, mockProject2],
  total: 2,
  skip: 0,
  limit: 50,
};

const mockMilestones: ProjectMilestone[] = [
  {
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
  },
  {
    id: 'm-2',
    project_id: 'proj-1',
    title: 'Aplicação de resina epóxi',
    description: 'Camada de fundo e acabamento',
    status: 'IN_PROGRESS',
    due_date: '2026-10-15',
    completion_date: null,
    display_order: 2,
    created_at: '2026-08-20T10:00:00Z',
    updated_at: '2026-08-20T10:00:00Z',
  },
  {
    id: 'm-3',
    project_id: 'proj-1',
    title: 'Instalação das traves e redes',
    description: 'Equipamentos esportivos',
    status: 'NEXT_STEPS',
    due_date: '2026-11-20',
    completion_date: null,
    display_order: 3,
    created_at: '2026-08-20T10:00:00Z',
    updated_at: '2026-08-20T10:00:00Z',
  },
];

const mockUpdates: ProjectUpdate[] = [
  {
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
    photos: ['https://example.com/piso1.jpg', 'https://example.com/piso2.jpg'],
    cost_impact: 4500,
    created_at: '2026-09-10T14:30:00Z',
  },
];

const mockProjectDetail: ProjectDetail = {
  ...mockProject1,
  milestones: mockMilestones,
  updates: mockUpdates,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderWithQuery = (ui: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('Construction & Improvement Projects Feature Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEffectiveIdentity.mockReturnValue({
      role: 'ADMINISTRATOR',
      userTypeIds: [],
      isSimulating: false,
    });
    vi.mocked(projectsApi.getProjects).mockResolvedValue(mockProjectsResponse);
    vi.mocked(projectsApi.getProjectDetail).mockResolvedValue(mockProjectDetail);
  });

  describe('BudgetVsActualProgressBar', () => {
    it('renders normal budget execution with progress bar and remaining amount', () => {
      render(
        <BudgetVsActualProgressBar
          totalBudget={100000}
          executedBudget={45000}
        />
      );

      expect(screen.getByText('45% Executado')).toBeInTheDocument();
      expect(screen.getByTestId('budget-progress-fill')).toHaveStyle({ width: '45%' });
      expect(screen.getByTestId('budget-progress-fill')).toHaveClass('bg-emerald-500');
    });

    it('renders budget overrun warning when executed budget exceeds total budget', () => {
      render(
        <BudgetVsActualProgressBar
          totalBudget={50000}
          executedBudget={55000}
        />
      );

      expect(screen.getByText(/Orçamento Estourado/i)).toBeInTheDocument();
      expect(screen.getByTestId('budget-progress-fill')).toHaveClass('bg-red-500');
    });
  });

  describe('MilestoneTimeline', () => {
    it('renders three milestone workflow categories', () => {
      render(
        <MilestoneTimeline
          milestones={mockMilestones}
          canManage={true}
        />
      );

      expect(screen.getByText('Feito')).toBeInTheDocument();
      expect(screen.getByText('Em Andamento')).toBeInTheDocument();
      expect(screen.getByText('Próximos Passos')).toBeInTheDocument();

      expect(screen.getByText('Demolição do piso antigo')).toBeInTheDocument();
      expect(screen.getByText('Aplicação de resina epóxi')).toBeInTheDocument();
      expect(screen.getByText('Instalação das traves e redes')).toBeInTheDocument();
    });

    it('handles add milestone click for managers', () => {
      const handleAdd = vi.fn();
      render(
        <MilestoneTimeline
          milestones={mockMilestones}
          canManage={true}
          onAddMilestone={handleAdd}
        />
      );

      fireEvent.click(screen.getByText('Novo Marco'));
      expect(handleAdd).toHaveBeenCalledTimes(1);
    });
  });

  describe('ProjectUpdateFeed', () => {
    it('renders updates with author, photos, and cost impact', () => {
      render(
        <ProjectUpdateFeed
          updates={mockUpdates}
          canPostUpdate={true}
          canDeleteUpdate={true}
        />
      );

      expect(screen.getByText('Primeira demão aplicada')).toBeInTheDocument();
      expect(screen.getByText('Piso devidamente lixado e selado.')).toBeInTheDocument();
      expect(screen.getByText(/Engenheiro Carlos/)).toBeInTheDocument();
      expect(screen.getByText(/Impacto/)).toBeInTheDocument();
    });
  });

  describe('ProjectSummaryCard', () => {
    it('renders project summary info and triggers onSelect when clicked', () => {
      const handleSelect = vi.fn();
      render(
        <ProjectSummaryCard
          project={mockProject1}
          onSelect={handleSelect}
          canManage={true}
        />
      );

      expect(screen.getByText('Reforma da Quadra')).toBeInTheDocument();
      expect(screen.getByText('Alfa Construtora')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Ver Detalhes'));
      expect(handleSelect).toHaveBeenCalledWith(mockProject1);
    });
  });

  describe('Modals Form Validation', () => {
    it('submits ProjectFormModal payload with numbers and dates', async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      const handleClose = vi.fn();

      render(
        <ProjectFormModal
          open={true}
          onClose={handleClose}
          onSubmit={handleSubmit}
        />
      );

      fireEvent.change(screen.getByLabelText(/Título da Obra/i), {
        target: { value: 'Nova Guarita' },
      });
      fireEvent.change(screen.getByLabelText(/Orçamento Previsto/i), {
        target: { value: '75000' },
      });

      fireEvent.click(screen.getByRole('button', { name: /Salvar Obra/i }));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Nova Guarita',
            total_budget: 75000,
          })
        );
      });
    });

    it('submits MilestoneFormModal correctly', async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      const handleClose = vi.fn();

      render(
        <MilestoneFormModal
          open={true}
          onClose={handleClose}
          onSubmit={handleSubmit}
        />
      );

      fireEvent.change(screen.getByLabelText(/Título do Marco/i), {
        target: { value: 'Fundação' },
      });
      fireEvent.click(screen.getByText('Salvar Marco'));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Fundação',
          })
        );
      });
    });

    it('submits ProjectUpdateModal with photos and cost impact', async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      const handleClose = vi.fn();

      render(
        <ProjectUpdateModal
          open={true}
          onClose={handleClose}
          onSubmit={handleSubmit}
        />
      );

      fireEvent.change(screen.getByLabelText(/Título da Atualização/i), {
        target: { value: 'Materiais Entregues' },
      });
      fireEvent.change(screen.getByLabelText(/Relato das Atividades/i), {
        target: { value: 'Cimento e areia descarregados' },
      });
      fireEvent.change(screen.getByLabelText(/Impacto Financeiro Adicional/i), {
        target: { value: '3000' },
      });
      fireEvent.change(screen.getByLabelText(/URLs das Fotos/i), {
        target: { value: 'https://example.com/p1.jpg\nhttps://example.com/p2.jpg' },
      });

      fireEvent.click(screen.getByText('Publicar Atualização'));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith({
          title: 'Materiais Entregues',
          content: 'Cimento e areia descarregados',
          cost_impact: 3000,
          photos: ['https://example.com/p1.jpg', 'https://example.com/p2.jpg'],
        });
      });
    });
  });

  describe('ConstructionTrackerPage Integration', () => {
    it('renders project list and filters projects by status', async () => {
      renderWithQuery(<ConstructionTrackerPage />);

      await waitFor(() => {
        expect(screen.getByText('Acompanhamento de Obras')).toBeInTheDocument();
        expect(screen.getByText('Reforma da Quadra')).toBeInTheDocument();
        expect(screen.getByText('Pintura Fachada')).toBeInTheDocument();
      });

      // Click filter tab "Em Andamento"
      fireEvent.click(screen.getByRole('button', { name: 'Em Andamento' }));
      expect(projectsApi.getProjects).toHaveBeenCalledWith({
        status: 'IN_PROGRESS',
      });
    });

    it('navigates to project detail view when selecting a card and allows going back', async () => {
      renderWithQuery(<ConstructionTrackerPage />);

      await waitFor(() => {
        expect(screen.getByText('Reforma da Quadra')).toBeInTheDocument();
      });

      const detailButtons = screen.getAllByText('Ver Detalhes');
      fireEvent.click(detailButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Voltar para Lista de Obras')).toBeInTheDocument();
        expect(screen.getByText('Marcos e Etapas da Obra')).toBeInTheDocument();
        expect(screen.getByText('Diário de Bordo e Fotos da Obra')).toBeInTheDocument();
      });

      // Go back to list
      fireEvent.click(screen.getByText('Voltar para Lista de Obras'));

      await waitFor(() => {
        expect(screen.getByText('Reforma da Quadra')).toBeInTheDocument();
      });
    });
  });
});
