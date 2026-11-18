export type Message = {
  id: string
  role: "user" | "assistant"
  paragraphs: string[]
  points?: string[]
}

export type Conversation = {
  id: string
  origin: "demo" | "local"
  title: string
  date: string
  messages: Message[]
}

export const demoConversations: Conversation[] = [
  {
    id: "pizarra",
    origin: "demo",
    title: "Diseño de la pizarra",
    date: "Hoy",
    messages: [
      { id: "pizarra-1", role: "user", paragraphs: ["¿Cómo dejamos más espacio para trabajar sin perder de vista los recursos del proyecto?"] },
      {
        id: "pizarra-2",
        role: "assistant",
        paragraphs: ["La pizarra de Kalka ya tiene una buena separación de funciones. En el prototipo, cada región tiene un papel concreto:"],
        points: [
          "El carril izquierdo cambia de sección y permanece visible.",
          "El panel contextual muestra las conversaciones, los proyectos o las fuentes de la vista activa.",
          "El área de trabajo ocupa el espacio libre y se amplía al plegar el panel.",
        ],
      },
    ],
  },
  {
    id: "referencias",
    origin: "demo",
    title: "Lectura de referencias",
    date: "Ayer",
    messages: [
      { id: "refs-1", role: "user", paragraphs: ["¿Qué patrones de las referencias podemos usar en el prototipo?"] },
      { id: "refs-2", role: "assistant", paragraphs: ["Usemos el carril y el panel independiente de Opportunities, la jerarquía documental de la cuarta captura y el plegado de Riter. Los dashboards oscuro y claro orientan el contraste de superficies y la densidad de datos."] },
    ],
  },
  {
    id: "navegacion",
    origin: "demo",
    title: "Navegación y recursos",
    date: "Lunes",
    messages: [
      { id: "nav-1", role: "user", paragraphs: ["¿Qué pasa con los recursos cuando cambio de vista?"] },
      { id: "nav-2", role: "assistant", paragraphs: ["Cada sección muestra sus propios recursos. La posición del carril y la preferencia de apertura se conservan durante la navegación."] },
    ],
  },
]

export const projects = [
  { id: "pizarra", name: "Pizarra React", area: "Producto", status: "En curso", date: "18 nov", progress: 72, detail: "Prototipo de escritorio inspirado en la estructura definida en Kalka." },
  { id: "referencias", name: "Archivo de referencias", area: "Diseño", status: "Listo", date: "17 nov", progress: 100, detail: "Cinco capturas organizadas por el patrón de interfaz que aportan." },
  { id: "componentes", name: "Sistema de componentes", area: "Diseño", status: "En revisión", date: "15 nov", progress: 54, detail: "Inventario de primitivas, iconos y tokens de superficie del espacio." },
  { id: "rutas", name: "Mapa de navegación", area: "Producto", status: "En curso", date: "13 nov", progress: 36, detail: "Relación entre secciones, recursos contextuales y áreas de trabajo." },
]

export const documents = [
  { id: "patrones", name: "Patrones de navegación", area: "Referencias visuales", detail: "Carril persistente, panel contextual independiente y espacio de trabajo flexible." },
  { id: "tokens", name: "Tokens de superficie", area: "Sistema visual", detail: "Base cálida y acento índigo de Kalka. En oscuro, superficies carbón con acentos lavanda." },
  { id: "pruebas", name: "Casos de interacción", area: "Verificación", detail: "Navegación entre secciones, teclado, cambio de tema y ajuste del panel contextual." },
]

export const periods = [7, 30, 90] as const
export type Period = typeof periods[number]

type MetricKey = "conversations" | "projects" | "resources" | "reviews"

export const metrics = {
  7: { conversations: 36, projects: 4, resources: 12, reviews: 8 },
  30: { conversations: 128, projects: 12, resources: 48, reviews: 24 },
  90: { conversations: 346, projects: 23, resources: 114, reviews: 63 },
} satisfies Record<Period, Record<MetricKey, number>>

export const activity = {
  7: [
    ["Lun", 4, 1], ["Mar", 6, 2], ["Mié", 4, 1], ["Jue", 7, 3],
    ["Vie", 8, 2], ["Sáb", 3, 1], ["Dom", 4, 2],
  ],
  30: [
    ["20 oct", 7, 3], ["23 oct", 12, 4], ["26 oct", 9, 3], ["29 oct", 16, 7],
    ["1 nov", 13, 5], ["4 nov", 18, 8], ["7 nov", 14, 4], ["10 nov", 21, 8],
    ["13 nov", 18, 6], ["16 nov", 24, 9], ["18 nov", 26, 11],
  ],
  90: [
    ["1 sep", 14, 6], ["9 sep", 23, 7], ["17 sep", 19, 6], ["25 sep", 28, 11],
    ["3 oct", 24, 13], ["11 oct", 34, 11], ["19 oct", 29, 16], ["27 oct", 42, 19],
    ["4 nov", 39, 17], ["12 nov", 47, 20], ["18 nov", 54, 23],
  ],
} satisfies Record<Period, [string, number, number][]>
