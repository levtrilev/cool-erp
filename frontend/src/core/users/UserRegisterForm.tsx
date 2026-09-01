import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AxiosError } from "axios";

// Импортируем КОНСТАНТУ Zod-схемы (проверьте точное имя файла в папке zod!)
import { registerAuthRegisterPostBody } from "@/api/generated/zod/authentication/authentication.schema"; 

// Импортируем хук мутации
import { useRegisterAuthRegisterPost } from "@/api/generated/authentication/authentication";

// Выводим тип TypeScript напрямую из Zod-схемы
type UserRegisterFormValues = z.infer<typeof registerAuthRegisterPostBody>;

// Тип для ошибки от FastAPI
interface FastAPIValidationError {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}

export const UserRegisterForm = () => {
  const navigate = useNavigate(); // Хук для редиректа
  
  const form = useForm<UserRegisterFormValues>({
    resolver: zodResolver(registerAuthRegisterPostBody),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      tenant_id: "",
    },
  });

  const registerMutation = useRegisterAuthRegisterPost();

  // const onSubmit = (data: UserRegisterFormValues) => {
  //   registerMutation.mutate(
  //     { data },
  //     {
  //       onSuccess: () => {
  //         console.log("Успешная регистрация!", data);
  //         form.reset();
  //         // Редирект на главную страницу после успешной регистрации
  //         navigate("/");
  //       },
  //       onError: (error) => {
  //         console.error("Ошибка регистрации:", error);
  //       },
  //     }
  //   );
  // };

  const onSubmit = (data: UserRegisterFormValues) => {
    registerMutation.mutate(
      { data },
      {
        onSuccess: () => {
          console.log("Успешная регистрация!");
          form.reset();
          navigate("/");
        },
        onError: (error) => {
          // Проверяем, что это ошибка от axios со статусом 422
          if (error instanceof AxiosError && error.response?.status === 422) {
            const errorData = error.response.data as FastAPIValidationError;
            
            // Список всех возможных полей нашей формы для строгой типизации
            const validFieldNames: (keyof UserRegisterFormValues)[] = [
              "name",
              "email",
              "password",
              "tenant_id",
            ];
            
            // Проходим по всем ошибкам от бэкенда
            errorData.detail?.forEach((err) => {
              // err.loc обычно выглядит как ["body", "имя_поля"]
              // Нас интересуют только ошибки тела запроса (body)
              if (err.loc[0] === "body") {
                const fieldName = err.loc[1] as keyof UserRegisterFormValues;
                
                // Проверяем, что это поле действительно существует в нашей форме
                if (validFieldNames.includes(fieldName)) {
                  form.setError(fieldName, {
                    type: "server",
                    message: err.msg,
                  });
                }
              }
            });
          } else {
            // Для других ошибок (500, сеть и т.д.) показываем общее сообщение
            console.error("Ошибка регистрации:", error);
            form.setError("root", {
              type: "server",
              message: "Произошла ошибка при регистрации. Попробуйте позже.",
            });
          }
        },
      }
    );
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Регистрация</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Имя</FormLabel>
                  <FormControl>
                    <Input placeholder="Иван Иванов" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="you@example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Пароль</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="••••••••" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tenant_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tenant ID (UUID)</FormLabel>
                  <FormControl>
                    <Input placeholder="123e4567-e89b-12d3-a456-426614174000" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
              {registerMutation.isPending ? "Регистрация..." : "Зарегистрироваться"}
            </Button>
            
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};
// import { zodResolver } from "@hookform/resolvers/zod";
// import { useForm } from "react-hook-form";
// import { z } from "zod";
// import { Button } from "@/components/ui/button";
// import {
//   Form,
//   FormControl,
//   FormField,
//   FormItem,
//   FormLabel,
//   FormMessage,
// } from "@/components/ui/form";
// import { Input } from "@/components/ui/input";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// // 1. Импортируем КОНСТАНТУ Zod-схемы (проверьте точное имя файла в папке zod!)
// import { registerAuthRegisterPostBody } from "@/api/generated/zod/authentication/authentication.schema"; 

// // 2. Импортируем хук мутации
// import { useRegisterAuthRegisterPost } from "@/api/generated/authentication/authentication";

// // 3. Выводим тип TypeScript напрямую из Zod-схемы
// type UserRegisterFormValues = z.infer<typeof registerAuthRegisterPostBody>;

// export const UserRegisterForm = () => {
//   // 4. Инициализируем форму с нашей сгенерированной схемой
//   const form = useForm<UserRegisterFormValues>({
//     resolver: zodResolver(registerAuthRegisterPostBody),
//     defaultValues: {
//       name: "",
//       email: "",
//       password: "",
//       tenant_id: "",
//     },
//   });

//   // 5. Хук для отправки данных
//   const registerMutation = useRegisterAuthRegisterPost();

//   const onSubmit = (data: UserRegisterFormValues) => {
//     registerMutation.mutate(
//       { data }, // Orval ожидает объект { data: ... } для POST-запросов
//       {
//         onSuccess: () => {
//           console.log("Успешная регистрация!", data);
//           form.reset(); // Очистить форму при успехе
//         },
//         onError: (error) => {
//           console.error("Ошибка регистрации:", error);
//         },
//       }
//     );
//   };

//   return (
//     <Card className="w-full max-w-md mx-auto mt-10">
//       <CardHeader>
//         <CardTitle>Регистрация</CardTitle>
//       </CardHeader>
//       <CardContent>
//         <Form {...form}>
//           <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
//             <FormField
//               control={form.control}
//               name="name"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>Имя</FormLabel>
//                   <FormControl>
//                     <Input placeholder="Иван Иванов" {...field} />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />

//             <FormField
//               control={form.control}
//               name="email"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>Email</FormLabel>
//                   <FormControl>
//                     <Input type="email" placeholder="you@example.com" {...field} />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />

//             <FormField
//               control={form.control}
//               name="password"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>Пароль</FormLabel>
//                   <FormControl>
//                     <Input type="password" placeholder="••••••••" {...field} />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />

//             <FormField
//               control={form.control}
//               name="tenant_id"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>Tenant ID (UUID)</FormLabel>
//                   <FormControl>
//                     <Input placeholder="123e4567-e89b-12d3-a456-426614174000" {...field} />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />

//             <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
//               {registerMutation.isPending ? "Регистрация..." : "Зарегистрироваться"}
//             </Button>
            
//           </form>
//         </Form>
//       </CardContent>
//     </Card>
//   );
// };