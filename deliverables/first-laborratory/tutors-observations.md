### Transcripción del Video

**Carlos Sehuanes:** ¿Es que allí solicitaba componentes en el laboratorio? O sea, por ejemplo...

**Carlos Oliveros (Profesor):** Sí, sí, pero tiene un arquetipo.

**Carlos Sehuanes:** Okay.

**Carlos Oliveros (Profesor):** Sí, es de un arquetipo. Arquetipo. Es que si es un arquetipo, yo espero las clases, pero a nivel de negocio. Por ejemplo, nosotros como somos orientados a objetos, la idea de cada clase es que abstraiga cosas de la vida del mundo real, ¿sí?

Entonces, en el mundo real, a nivel de negocio, ¿tú qué entidades vas a tener?

**Carlos Sehuanes:** Eh... como reservas, Proveedores... cliente o turista...

**Carlos Oliveros (Profesor):** Exacto, esas son las entidades que tienes que plasmar en el arquetipo.

¿Cómo lo tienes que plasmar? Es muy parecido a lo que habías hecho en la clase, muy parecido a eso. ¿Qué pasa? Que esto es a un nivel más alto, ¿sí?

Por ejemplo, te lo voy a poner, clases heredadas. Vamos a llegar a ese nivel. Vas a poner las clases como las clases padres principales, ¿cierto?, sin atributos específicos, o sea, sin interfaces, como quien dice.

**David Hasbúm:** O sea, ¿las entidades nada más?

**Carlos Sehuanes:** Solamente los nombres de las clases.

**Carlos Oliveros (Profesor):** Y cómo se relacionan esas clases principales entre sí con las demás.

**Carlos Oliveros (Profesor):** Muy general, el más alto nivel posible.

**Carlos Sehuanes:** Ah, okay.

**Carlos Oliveros (Profesor):** ¿Y qué tiene que tener? O sea, voy a tener la entidad de reserva, la entidad de proveedores, la entidad de turistas, ¿sí?, y cómo se relacionan entre sí. 

Aquí, en este laboratorio que estamos haciendo, es a más alto nivel todavía, apenas vamos a entrar en detalle, ¿listo? Ahora, muéstrame el de... Ese de componentes de ahí.

**Carlos Oliveros (Profesor):** Esta es la de... la de contexto. Mira, es turista...


**Carlos Sehuanes:** Yo ahorita me puse a revisar... en el caso del diagrama de casos de uso, él también utilizó la librería de Mermaid para armar Markdown, pero no me dejaba... Conseguí esta alternativa de...

**Carlos Oliveros (Profesor):** Carlos, muéstrame el de componentes.

**Carlos Sehuanes:** Claro que sí, el aqui está

**Carlos Oliveros (Profesor):** Okay... Este está bien. El de componentes, ¿cierto?, aquí sí lo vamos a ver, aquí sí vemos cómo se conectan. Por ejemplo, sabemos que hay un mediador, ¿cierto?, un punto de entrada ahí, con servicio de producción, usuarios y seguridad.

Esto yo lo vería entonces más como un módulo de autorización y autenticación, el famoso Auth...

Si lo quieres llamar así por ahora, está bien. Catálogo está bien, las reservas... Notificaciones, esto yo simplemente lo llamaría más como reservas, e implícitamente sabemos que tenemos que manejar las notificaciones.

Está bien, a nivel de componentes está bien. ¿Qué le mejoraría yo? De pronto llamar a esto como un servicio, llamar a esto como un servicio, y eliminar lo interno. A este nivel todavía no vamos a ver ese detalle. O sea, aqui estamos a alto nivel todavía no, todavía no hemos definido ni la base de datos, ni la arquitectura, o sea, sí, pero en este diagrama de pronto no lo vamos a plasmar todavía.

**Carlos Oliveros (Profesor):** ¿Qué vamos a hacer ahora? Este, ¿por qué no vamos a ver ese detalle? Porque este es el primer diagrama. Este diagrama tiene una particularidad, que es iterativo. Entonces, esta primera versión la hacemos a alto nivel. Este mismo lo vamos a ir descomponiendo, detallando, hasta llegar a un nivel con más detalle.

Lo mismo para el de clases, lo vamos a ir bajando...

**Carlos Sehuanes:** Así como en el de clases nada más serían los nombres y bueno, que estén conectados...

**Carlos Oliveros (Profesor):** Cómo se relacionan esos componentes. Entonces no vamos a ver ese nivel de detalle. Sí vamos a llegar, vamos a llegar a algo muy parecido a esto, de hecho, podemos llegar a algo así, pero inicialmente alto nivel. ¿Ya? Y recuerda que esto es iterativo, sobre todo este diagrama de componentes.

Entonces te damos para desarrollar uno, dos o tres y lo demás... Listo.

Muestrame el de Arquitectura

**David hasbúm:** Contexto... Son los usuarios y actores...

**Carlos Oliveros (Profesor):** Sí, el diagrama de contexto. El de DCA

**Carlos Oliveros (Profesor):** A ver ese... ¿Este qué te dice? Te dice con quién se relaciona nuestra aplicación de frontera hacia afuera. Eso es todo aquí, básicamente.

¿Entonces qué me dice? Que hay unos contextos de comunicación, un usuario que lo usa, y de gestión, ¿esto qué es? Entidades externas de destino, ¿qué sería eso?

**Carlos Oliveros (Profesor):** Un operador... Como un operador, ¿no? Un operador turístico.

**Carlos Sehuanes:** Okay, o sea, creo que está mencionado entre los actores, ya le digo...

**Carlos Oliveros (Profesor):** O sea, el de destino como quien dice es quien va a gestionar la llegada allá. Eso es un operador. Que hay diferentes tipos de operadores, sí, restaurante, hoteles, no sé, guía turístico. Le llaman a nivel general como cualquier servicio... Esto puede ser parte de esto. Turista nacional e internacional, turista, administrador de la plataforma también puede existir, administrador, ¿okay? Puede ser también.

Esto estaría de un poquito de más. A nosotros no nos interesa internamente cómo se hace la comunicación. Solamente cómo se comunica esto con esto, exactamente. Proveedor Cloud, esto no va. *(risas)* Esto es ya arquitectura, a nosotros todavía no nos interesa cómo vamos a ver la arquitectura.

Fuentes externas de datos, redes sociales, esto sí puede ser. Esto sí puede ser. Ahora, no sé si sea horizontal esa relación. ¿Por qué? Porque yo puedo... Puede ser, no te estoy diciendo que esté mal, pero de pronto yo más bien uso las redes sociales. O sea, están por debajo de mí, yo las uso para extraer información. Para mí es así, piensen si de pronto va aquí o si de pronto sí debería ir aquí.

**Carlos Sehuanes:** Entonces si se deja horaizontal o se pone en otro lugar depende de la desición que tomemos como arquitectos

**Carlos Oliveros (Profesor):** Exactamente, si para ustedes es que ustedes van a usar esa información o simplemente nos vamos a integrar con ella y tenemos una relación par a par.

Pasarela de pago no se va a incluir en el sistema, entonces esto no iría. Listo, sería eso.
