workspace "Маркетплейс" "C4 Container диаграмма маркетплейса" {

  model {
    buyer = person "Покупатель" "Смотрит товары и оформляет заказы"
    seller = person "Продавец" "Управляет каталогом и выполняет заказы"
    admin = person "Поддержка/Модерация" "Решает спорные ситуации и модерирует контент"

    marketplace = softwareSystem "Маркетплейс" "Цифровая платформа для размещения товаров и оформления заказов" {

      web = container "Веб/Мобайл фронтенд" "Интерфейс для покупателей и продавцов" "Web/Mobile"
      apiGateway = container "API Gateway / BFF" "Единая точка входа: маршрутизация, сессии, базовые проверки" "Nginx/Envoy/BFF"

      userSvc = container "Сервис пользователей" "Пользователи, роли, профиль продавца" "Service"
      catalogSvc = container "Сервис каталога" "Товары, категории, атрибуты, управление каталогом" "Service"
      recSvc = container "Сервис рекомендаций" "Персонализированная лента товаров" "Service"
      orderSvc = container "Сервис заказов" "Оформление заказа и жизненный цикл статусов" "Service"
      paymentSvc = container "Сервис платежей" "Расчёт, учёт платежей, проводки (ledger)" "Service"
      notifSvc = container "Сервис уведомлений" "Email/SMS/push о статусах и событиях" "Service"

      eventBus = container "Шина событий" "Асинхронное взаимодействие сервисов" "Kafka/RabbitMQ"
      userDb = container "БД пользователей" "Данные пользователей (владение User Service)" "PostgreSQL"
      catalogDb = container "БД каталога" "Данные каталога (владение Catalog Service)" "PostgreSQL"
      orderDb = container "БД заказов" "Данные заказов (владение Order Service)" "PostgreSQL"
      paymentDb = container "БД платежей" "Данные платежей и учёта (владение Payment Service)" "PostgreSQL"
    }

    buyer -> web "Пользуется"
    seller -> web "Пользуется"
    admin -> web "Пользуется"

    web -> apiGateway "HTTPS"
    apiGateway -> userSvc "REST/gRPC (sync)"
    apiGateway -> catalogSvc "REST/gRPC (sync)"
    apiGateway -> recSvc "REST/gRPC (sync)"
    apiGateway -> orderSvc "REST/gRPC (sync)"

    userSvc -> userDb "Чтение/запись"
    catalogSvc -> catalogDb "Чтение/запись"
    orderSvc -> orderDb "Чтение/запись"
    paymentSvc -> paymentDb "Чтение/запись"

    orderSvc -> paymentSvc "Инициация оплаты (sync)"

    orderSvc -> eventBus "Публикует OrderCreated/OrderStatusChanged (async)"
    paymentSvc -> eventBus "Публикует PaymentAuthorized/PaymentFailed (async)"
    notifSvc -> eventBus "Подписывается и отправляет уведомления (async)"
    recSvc -> eventBus "Подписывается на события поведения/заказов (async)"
  }

  views {
      container marketplace containers {
        title "Контейнерная диаграмма маркетплейса"
        include *
        autoLayout lr
      }

    styles {
      element "Person" {
        shape person
      }
      element "Container" {
        shape roundedbox
      }
      element "Database" {
        shape cylinder
      }
    }
  }
}