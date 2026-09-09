// import { useState, useEffect } from "react";
// import { useForm, Controller } from "react-hook-form";
// import { zodResolver } from "@hookform/resolvers/zod";
// import { z } from "zod";
// import { useQueryClient } from "@tanstack/react-query";
// import { Loader2, Check } from "lucide-react";
// import { useToast } from "@/components/ui/use-toast";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Textarea } from "@/components/ui/textarea";
// import { Checkbox } from "@/components/ui/checkbox";
// import {
//   Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
// } from "@/components/ui/dialog";
// import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
// import {
//   Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
// } from "@/components/ui/table";

// // Orval хуки
// import { useUpdateRoleRolesRoleIdPut } from "@/api/generated/roles/roles";
// import { useGetSectionsSectionsGet } from "@/api/generated/sections/sections";
// import { useReadUsersUsersGet } from "@/api/generated/users/users";
// import type { RoleResponseSchema, PermissionCreateSchema } from "@/api/generated/fastAPI.schemas";

// // Схема валидации
// const roleSchema = z.object({
//   name: z.string().min(1, "Название обязательно"),
//   description: z.string().optional(),
// });
// type RoleFormData = z.infer<typeof roleSchema>;

// // Заглушка для типов документов (в будущем можно получать с бэкенда)
// const AVAILABLE_DOCTYPES = [
//   { doctype: "invoices", doctype_name: "Счета-фактуры" },
//   { doctype: "orders", doctype_name: "Заказы" },
//   { doctype: "contracts", doctype_name: "Договоры" },
//   { doctype: "payments", doctype_name: "Платежи" },
// ];

// interface EditRoleModalProps {
//   open: boolean;
//   onOpenChange: (open: boolean) => void;
//   role: RoleResponseSchema | null;
//   onRoleSaved: (id: string, name: string) => void;
// }

// export function EditRoleModal({ open, onOpenChange, role, onRoleSaved }: EditRoleModalProps) {
//   const queryClient = useQueryClient();
//   const { toast } = useToast();
//   const isEdit = !!role;

//   const { control, handleSubmit, reset, formState: { isDirty } } = useForm<RoleFormData>({
//     resolver: zodResolver(roleSchema),
//     defaultValues: { name: "", description: "" },
//   });

//   // Состояния для вкладок
//   const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>([]);
//   const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
//   const [permissions, setPermissions] = useState<PermissionCreateSchema[]>([]);

//   // Загрузка данных для вкладок
//   const { data: sectionsData } = useGetSectionsSectionsGet({ limit: 1000, skip: 0 });
//   const { data: usersData } = useReadUsersUsersGet({ limit: 1000, skip: 0 });
  
//   const sections = sectionsData?.data?.items ?? [];
//   const users = usersData?.items ?? [];

//   const saveMutation = useUpdateRoleRolesRoleIdPut();

//   // Инициализация формы при открытии
//   useEffect(() => {
//     if (open) {
//       if (role) {
//         reset({ name: role.name, description: role.description || "" });
//         setSelectedSectionIds(role.section_ids || []);
//         // В реальном проекте нужно загружать permissions и user_ids для этой роли
//         // Пока оставим пустыми для демонстрации структуры
//         setPermissions([]); 
//         setSelectedUserIds([]);
//       } else {
//         reset({ name: "", description: "" });
//         setSelectedSectionIds([]);
//         setSelectedUserIds([]);
//         setPermissions(AVAILABLE_DOCTYPES.map(d => ({
//           doctype: d.doctype,
//           doctype_name: d.doctype_name,
//           role_id: "", // Заполнится на бэкенде
//           tenant_id: role?.tenant_id || "", // Заполнится на бэкенде
//           full_access: false,
//           author: false,
//           reader: false,
//           editor: false,
//           can_delete: false,
//         })));
//       }
//     }
//   }, [open, role, reset]);

//   const onSubmit = async (data: RoleFormData) => {
//     // Собираем названия разделов
//     const sectionNames = sections
//       .filter(s => selectedSectionIds.includes(s.id))
//       .map(s => s.name);

//     const payload = {
//       name: data.name,
//       description: data.description,
//       tenant_id: role?.tenant_id || "00000000-0000-0000-0000-000000000000", // В реальности берем из сессии
//       section_ids: selectedSectionIds,
//       section_names: sectionNames,
//       permissions: permissions,
//       user_ids: selectedUserIds,
//     };

//     saveMutation.mutate(
//       { data: payload, roleId: role?.id },
//       {
//         onSuccess: async (res) => {
//           const savedRole = res.data;
//           // Правило №24: invalidateQueries -> onOpenChange -> onRoleSaved
//           queryClient.invalidateQueries({ queryKey: ["roles"] });
//           onOpenChange(false);
//           await onRoleSaved(savedRole.id, savedRole.name);
//         },
//         onError: () => {
//           toast({ variant: "destructive", title: "Ошибка", description: "Не удалось сохранить роль" });
//         },
//       }
//     );
//   };

//   const togglePermission = (doctype: string, field: keyof PermissionCreateSchema) => {
//     setPermissions(prev => prev.map(p => 
//       p.doctype === doctype ? { ...p, [field]: !p[field] } : p
//     ));
//   };

//   return (
//     <Dialog open={open} onOpenChange={onOpenChange}>
//       <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
//         <DialogHeader>
//           <DialogTitle>{isEdit ? `Редактирование: ${role.name}` : "Создание роли"}</DialogTitle>
//         </DialogHeader>

//         <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
//           <Tabs defaultValue="main" className="w-full">
//             <TabsList className="grid w-full grid-cols-4">
//               <TabsTrigger value="main">Основное</TabsTrigger>
//               <TabsTrigger value="sections">Разделы</TabsTrigger>
//               <TabsTrigger value="permissions">Полномочия</TabsTrigger>
//               <TabsTrigger value="users">Пользователи</TabsTrigger>
//             </TabsList>

//             {/* Вкладка 1: Основное */}
//             <TabsContent value="main" className="space-y-4 pt-2">
//               <div className="space-y-2">
//                 <label className="text-sm font-medium">Название роли</label>
//                 <Controller
//                   name="name"
//                   control={control}
//                   render={({ field, fieldState }) => (
//                     <>
//                       <Input {...field} placeholder="Например: Бухгалтер" />
//                       {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
//                     </>
//                   )}
//                 />
//               </div>
//               <div className="space-y-2">
//                 <label className="text-sm font-medium">Описание</label>
//                 <Controller
//                   name="description"
//                   control={control}
//                   render={({ field }) => (
//                     <Textarea {...field} placeholder="Описание роли..." rows={3} />
//                   )}
//                 />
//               </div>
//             </TabsContent>

//             {/* Вкладка 2: Разделы */}
//             <TabsContent value="sections" className="pt-2">
//               <div className="rounded-md border">
//                 <Table>
//                   <TableHeader>
//                     <TableRow className="h-10 hover:bg-transparent">
//                       <TableHead className="w-[50px]"></TableHead>
//                       <TableHead>Название раздела</TableHead>
//                     </TableRow>
//                   </TableHeader>
//                   <TableBody>
//                     {sections.map((section) => (
//                       <TableRow key={section.id} className="py-1">
//                         <TableCell>
//                           <Checkbox
//                             checked={selectedSectionIds.includes(section.id)}
//                             onCheckedChange={(checked) => {
//                               setSelectedSectionIds(prev => 
//                                 checked ? [...prev, section.id] : prev.filter(id => id !== section.id)
//                               );
//                             }}
//                           />
//                         </TableCell>
//                         <TableCell className="py-1 font-medium">{section.name}</TableCell>
//                       </TableRow>
//                     ))}
//                   </TableBody>
//                 </Table>
//               </div>
//             </TabsContent>

//             {/* Вкладка 3: Полномочия */}
//             <TabsContent value="permissions" className="pt-2">
//               <div className="rounded-md border overflow-x-auto">
//                 <Table>
//                   <TableHeader>
//                     <TableRow className="h-10 hover:bg-transparent">
//                       <TableHead>Тип документа</TableHead>
//                       <TableHead className="text-center">Полный доступ</TableHead>
//                       <TableHead className="text-center">Редактор</TableHead>
//                       <TableHead className="text-center">Автор</TableHead>
//                       <TableHead className="text-center">Читатель</TableHead>
//                       <TableHead className="text-center">Удаление</TableHead>
//                     </TableRow>
//                   </TableHeader>
//                   <TableBody>
//                     {permissions.map((perm) => (
//                       <TableRow key={perm.doctype} className="py-1">
//                         <TableCell className="py-1 font-medium">{perm.doctype_name || perm.doctype}</TableCell>
//                         <TableCell className="text-center">
//                           <Checkbox checked={perm.full_access} onCheckedChange={() => togglePermission(perm.doctype, "full_access")} />
//                         </TableCell>
//                         <TableCell className="text-center">
//                           <Checkbox checked={perm.editor} onCheckedChange={() => togglePermission(perm.doctype, "editor")} />
//                         </TableCell>
//                         <TableCell className="text-center">
//                           <Checkbox checked={perm.author} onCheckedChange={() => togglePermission(perm.doctype, "author")} />
//                         </TableCell>
//                         <TableCell className="text-center">
//                           <Checkbox checked={perm.reader} onCheckedChange={() => togglePermission(perm.doctype, "reader")} />
//                         </TableCell>
//                         <TableCell className="text-center">
//                           <Checkbox checked={perm.can_delete} onCheckedChange={() => togglePermission(perm.doctype, "can_delete")} />
//                         </TableCell>
//                       </TableRow>
//                     ))}
//                   </TableBody>
//                 </Table>
//               </div>
//             </TabsContent>

//             {/* Вкладка 4: Пользователи */}
//             <TabsContent value="users" className="pt-2">
//               <div className="rounded-md border">
//                 <Table>
//                   <TableHeader>
//                     <TableRow className="h-10 hover:bg-transparent">
//                       <TableHead className="w-[50px]"></TableHead>
//                       <TableHead>Имя</TableHead>
//                       <TableHead>Email</TableHead>
//                     </TableRow>
//                   </TableHeader>
//                   <TableBody>
//                     {users.map((user) => (
//                       <TableRow key={user.id} className="py-1">
//                         <TableCell>
//                           <Checkbox
//                             checked={selectedUserIds.includes(user.id)}
//                             onCheckedChange={(checked) => {
//                               setSelectedUserIds(prev => 
//                                 checked ? [...prev, user.id] : prev.filter(id => id !== user.id)
//                               );
//                             }}
//                           />
//                         </TableCell>
//                         <TableCell className="py-1 font-medium">{user.name}</TableCell>
//                         <TableCell className="py-1 text-muted-foreground">{user.email}</TableCell>
//                       </TableRow>
//                     ))}
//                   </TableBody>
//                 </Table>
//               </div>
//             </TabsContent>
//           </Tabs>

//           <DialogFooter>
//             <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
//               Отмена
//             </Button>
//             <Button type="submit" disabled={saveMutation.isPending}>
//               {saveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
//               <Check className="mr-2 h-4 w-4" />
//               Сохранить
//             </Button>
//           </DialogFooter>
//         </form>
//       </DialogContent>
//     </Dialog>
//   );
// }