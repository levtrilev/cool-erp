import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Combobox } from '@/components/ui/combobox';
import { Input } from '@/components/ui/input';
import { useReadUsersUsersGet } from '@/api/generated/users/users';
import { useListAccessAuditApiV1AuditAccessGet, useListDataAuditApiV1AuditDataGet } from '@/api/generated/audit-access-logs/audit-access-logs';


interface AuditPageProps {
  className?: string;
}

const getEntityTypeName = (entityType: string): string => {
  const entityNames: Record<string, string> = {
    note: 'Заметки',
    section: 'Разделы',
    user: 'Пользователи',
    role: 'Роли',
    goods: 'Товары',
    warehouse: 'Склады',
    tenant: 'Организации',
    doctype: 'Типы документов',
  };
  return entityNames[entityType] || entityType;
};

export const AuditPage = ({ className }: AuditPageProps) => {
  const [activeTab, setActiveTab] = useState<'access' | 'data'>('access');
  const [page, setPage] = useState(0);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string | undefined>(undefined);
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined);

  const entityTypeOptions = [
    { value: undefined, label: 'Все типы' },
    { value: 'note', label: 'Заметки' },
    { value: 'goods', label: 'Товары' },
    { value: 'warehouse', label: 'Склады' },
    { value: 'user', label: 'Пользователи' },
    { value: 'section', label: 'Разделы' },
    { value: 'role', label: 'Роли' }
  ];

  const actionOptions = [
    { value: undefined, label: 'Все действия' },
    { value: 'create', label: 'Создание' },
    { value: 'update', label: 'Обновление' },
    { value: 'delete', label: 'Удаление' }
  ];

  const { data: users } = useReadUsersUsersGet();
  const userItems = (users as any)?.items || (users as any)?.data?.items || []; 
  const [userEmailFilter, setUserEmailFilter] = useState<string | undefined>(undefined);
  const [startDate, setStartDate] = useState<string | undefined>(undefined);
  const [endDate, setEndDate] = useState<string | undefined>(undefined);

  const {
    data: accessLogs,
    isLoading: isLoadingAccess,
    refetch: refetchAccess,
  } = useListAccessAuditApiV1AuditAccessGet({
    skip: page * 20,
    limit: 20,
  }, {
    query: {
      refetchOnMount: 'always',
    },
  });

  const {
    data: dataChanges,
    isLoading: isLoadingData,
    refetch: refetchData,
  } = useListDataAuditApiV1AuditDataGet({
    skip: page * 20,
    limit: 20,
    entity_type: entityTypeFilter,
    action: actionFilter,
    user_email: userEmailFilter,
    start_date: startDate,
    end_date: endDate,
  }, {
    query: {
      refetchOnMount: 'always',
    },
  });

  const handleRefresh = () => {
    if (activeTab === 'access') {
      refetchAccess();
    } else {
      refetchData();
    }
  };

  const handleExport = async () => {
    // Формируем URL с текущими параметрами фильтров
    const params = new URLSearchParams();
    if (entityTypeFilter) params.append('entity_type', entityTypeFilter);
    if (actionFilter) params.append('action', actionFilter);
    if (userEmailFilter) params.append('user_email', userEmailFilter);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
      // Делаем запрос через fetch, чтобы передать куки (credentials)
        const response = await fetch(`http://localhost:8000/api/v1/audit/export?${params.toString()}`, {
          credentials: 'include',
      });

      if (!response.ok) {
        alert('Ошибка при экспорте данных');
        return;
      }

      // Превращаем ответ в Blob (файл) и скачиваем его
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audit.csv'; // Имя файла
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Ошибка экспорта:', error);
      alert('Не удалось скачать файл');
    }
  
  };

  return (
    <div className={`p-6 ${className}`}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Аудит</h1>
        <div>
          <Button onClick={handleRefresh} variant="outline">
            Обновить
            </Button>
              {activeTab === 'data' && (
               <Button  onClick={handleExport} variant="outline" className="ml-2">
                Экспорт в CSV
            </Button>
              )}
        </div>
      </div>


      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'access' | 'data')}>
        <TabsList>
          <TabsTrigger value="access">Логи входа</TabsTrigger>
          <TabsTrigger value="data">Изменения данных</TabsTrigger>
        </TabsList>

 <TabsContent value="access">
          {activeTab === 'access' && (
            <>
              {isLoadingAccess ? (
                <div className="text-center py-8">Загрузка...</div>
              ) : accessLogs?.data?.items?.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Пользователь</TableHead>
                      <TableHead>Действие</TableHead>
                      <TableHead>Ресурс</TableHead>
                      <TableHead>Статус</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead>Дата</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {accessLogs.data.items.map((log: any) => (
                      <TableRow key={log.id}>
                        <TableCell>{log.user_email || 'Система'}</TableCell>
                        <TableCell>{log.action}</TableCell>
                        <TableCell>{log.resource}</TableCell>
                        <TableCell>
                          <Badge variant={log.status === 'success' ? 'default' : 'destructive'} className={log.status === 'success' ? 'bg-green-600 text-white hover:bg-green-700' : ''}>
                            {log.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{log.ip_address}</TableCell>
                        <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">Логов пока нет</div>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="data">
          {activeTab === 'data' && (
            <>
              <div className="flex gap-4 mb-4">
                {/* 3. Поиск по email */}
                <Combobox
                  value={userEmailFilter || ''}
                  onValueChange={(value) => {
                    setUserEmailFilter(value || undefined);
                    setPage(0);
                  }}
                  options={userItems}
                  getOptionLabel={(user: any) => user?.email || ''}
                  getOptionValue={(user: any) => user?.email || ''}
                  placeholder="Поиск по email"
                  className="w-[240px]"
                />

                {/* 1. Тип сущности */}
                <Select
                  value={entityTypeFilter || 'undefined'}
                  onValueChange={(value) => {
                    setEntityTypeFilter(value === 'undefined' ? undefined : value);
                    setPage(0);
                  }}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Тип сущности" />
                  </SelectTrigger>
                  <SelectContent>
                    {entityTypeOptions.map((option) => (
                      <SelectItem key={option.value || 'all'} value={option.value || 'undefined'}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* 2. Действие */}
                <Select
                  value={actionFilter || 'undefined'}
                  onValueChange={(value) => {
                    setActionFilter(value === 'undefined' ? undefined : value);
                    setPage(0);
                  }}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Действие" />
                  </SelectTrigger>
                  <SelectContent>
                    {actionOptions.map((option) => (
                      <SelectItem key={option.value || 'all'} value={option.value || 'undefined'}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* 4. Дата С */}
                <div className="flex items-center gap-2">
                  <span>С</span>
                  <Input
                    type="date"
                    value={startDate || ''}
                    onChange={(e) => {
                      setStartDate(e.target.value || undefined);
                      setPage(0);
                    }}
                    className="w-[150px]"
                  />
                </div>

                {/* 5. Дата По */}
                <div className="flex items-center gap-2">
                  <span>По</span>
                  <Input
                    type="date"
                    value={endDate || ''}
                    onChange={(e) => {
                      setEndDate(e.target.value || undefined);
                      setPage(0);
                    }}
                    className="w-[150px]"
                  />
                </div>
              </div>
        
              {isLoadingData ? (
                <div className="text-center py-8">Загрузка...</div>
              ) : dataChanges?.data?.items?.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Пользователь</TableHead>
                      <TableHead>Сущность</TableHead>
                      <TableHead>Действие</TableHead>
                      <TableHead>Изменения</TableHead>
                      <TableHead>Дата</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataChanges.data.items.map((change: any) => (
                      <TableRow key={change.id}>
                        <TableCell>{change.user_email || 'Система'}</TableCell>
                        <TableCell>{change.entity_name ? `${getEntityTypeName(change.entity_type)}: ${change.entity_name} (${change.entity_id})` : `${getEntityTypeName(change.entity_type)}: ${change.entity_id}`}</TableCell>
                        <TableCell>{change.action}</TableCell>
                        <TableCell>
                          {change.changes ? (
                            <div className="space-y-1">
                              {Object.entries(change.changes as Record<string, any>).map(([field, { old, new: newValue }]) => (
                                <div key={field} className="text-sm">
                                  <span className="font-medium">{field}:</span> {old} → {newValue}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span>Нет изменений</span>
                          )}
                        </TableCell>
                        <TableCell>{new Date(change.created_at).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">Логов пока нет</div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

        <div className="flex justify-center mt-6 space-x-4">
          <Button
            onClick={() => setPage(page - 1)}
            disabled={page === 0}
            variant="outline"
          >
            Назад
          </Button>
          <Button
            onClick={() => setPage(page + 1)}
            variant="outline"
          >
            Вперед
          </Button>
        </div>
      </div>
    );
  };
