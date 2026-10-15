# JVM adapter — Java, Kotlin, Scala, Groovy

## Components

A component is a **package** (`com.acme.billing`). Packages map to folders,
so the default `directory` strategy works once the source root points at
the package root:

```json
"source_roots": ["src/main/java"]            // or src/main/kotlin, app/src/main/java ...
```

Multi-module builds (Maven modules, Gradle subprojects) list each module's
source root. Component ids then get the root as a prefix; switch to the
`explicit` strategy if module names are clearer than package names.

## Size

`scc` or the built-in counter are fine. For statement counts or complexity
per package, any static analysis platform that exports per-package metrics
can be fed through `size_components.py --from-json`.

## Dependencies

`jdeps` (ships with the JDK) reads bytecode, so it also sees
fully-qualified references that never appear in an `import`:

```bash
./mvnw -q -DskipTests package            # or ./gradlew classes
jdeps -verbose:package -filter:none target/classes \
  | awk '$2 == "->" { print $1 "\t" $3 }' \
  | python3 "$SKILL_DIR/scripts/convert_edges.py" --workspace decomposition \
      --kind namespaces --tool jdeps -
```

`jdeps` does not see reflection, Spring/CDI wiring by name, or events.

## Fitness functions

| Library | Notes |
|---|---|
| **ArchUnit** | The reference for Java/Kotlin architecture tests (JUnit 4/5). |
| **Spring Modulith** | For Spring Boot: treats top-level packages under the app as modules and verifies their boundaries. |
| **Konsist** | Kotlin-first, also checks declarations and naming. |
| **jMolecules** | Annotations for DDD concepts, with ArchUnit rules. |

ArchUnit, Phase 4 (no cycles) and Phase 5 (domain boundary):

```java
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

@AnalyzeClasses(packages = "com.acme")
class ArchitectureTest {

  @ArchTest // RFC-0008
  static final ArchRule components_are_free_of_cycles =
      slices().matching("com.acme.(*)..").should().beFreeOfCycles();

  @ArchTest // RFC-0011
  static final ArchRule ordering_does_not_depend_on_reporting =
      noClasses().that().resideInAPackage("com.acme.ordering..")
          .should().dependOnClassesThat().resideInAPackage("com.acme.reporting..")
          .because("RFC-0011: reporting reads from ordering, never the reverse");
}
```

Phase 3 (no orphaned classes in a flattened parent):

```java
  @ArchTest
  static final ArchRule no_classes_directly_in_orders =
      noClasses().should().resideInAPackage("com.acme.orders")   // exact package, no ".."
          .because("RFC-0006: orders was flattened into orders.core / orders.pricing");
```

Spring Modulith (Phase 5, once domains are top-level packages):

```java
@Test
void verifiesModularStructure() {
  ApplicationModules.of(Application.class).verify();
}
```

Konsist (Kotlin):

```kotlin
@Test
fun `ordering does not depend on reporting`() {
    Konsist.scopeFromProject().assertArchitecture {
        val ordering = Layer("Ordering", "com.acme.ordering..")
        val reporting = Layer("Reporting", "com.acme.reporting..")
        reporting.dependsOn(ordering)
        ordering.dependsOnNothing()
    }
}
```

ArchUnit's `FreezingArchRule` gives a baseline for existing violations.

## Pitfalls

- Split packages across modules make one component appear twice; use the
  `explicit` strategy.
- Lombok, MapStruct and other annotation processors generate code in
  `target/generated-sources`; keep it excluded.
- Spring beans injected by interface hide the implementation dependency:
  the code depends on `PaymentPort`, the runtime on `StripeAdapter` in
  another package. Check the wiring configuration.
- JPA entities shared across packages are coupling through the database;
  list them in Phase 4.
