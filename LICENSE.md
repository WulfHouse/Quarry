# WulfHouse Source-Available Non-Compete License (WSANCL)

**Version 1.0** — December 22, 2025

> **Note:** This license is source-available. It is **NOT** an OSI-approved open-source license.

---

## 0. PARTIES

**"Licensor"** means WulfHouse. WulfHouse is the public-facing name used by Alexander Rose Wulf (an individual) for stewardship and licensing of the Licensed Work, and includes any successor that lawfully acquires control of the Licensed Work.

**"You"** (or **"Licensee"**) means the individual or legal entity exercising rights under this license.

**"Affiliate"** means an entity that directly or indirectly controls, is controlled by, or is under common control with a party, where "control" means the power to direct management or policies (by ownership, contract, or otherwise).

---

## 1. DEFINITIONS

### 1.1 "Licensed Work"

"Licensed Work" means the software, tooling, and documentation distributed by Licensor under this license, including any portion of it, and any Derivative Work of it that You make.

### 1.2 "Derivative Work"

"Derivative Work" means any work based on the Licensed Work for which permission is required under copyright law, including modifications, adaptations, or works that incorporate substantial portions of the Licensed Work.

### 1.3 "Source Code"

"Source Code" means the preferred form for making modifications, including build scripts and configuration files necessary to generate object code.

### 1.4 "Object Code"

"Object Code" means any form of the Licensed Work that is not Source Code, including compiled binaries.

### 1.5 "Output"

"Output" means artifacts You produce by using the Licensed Work in its intended role as a programming language toolchain and developer tools, such as compiled binaries, libraries, packages, documentation generated for Your project, test results, benchmarks, and build artifacts, excluding the Licensed Work itself and excluding any Derivative Work of the Licensed Work.

### 1.6 "Redistributable Components"

"Redistributable Components" means those parts of the Licensed Work that are reasonably necessary for recipients to run, link, or execute Output produced by the Licensed Work, such as runtime libraries, standard libraries, headers, link-time artifacts, and similar components, when distributed solely under the Runtime Exception in Section 4.2.

### 1.7 "Commercialize"

"Commercialize" means to sell, license for a fee, monetize, or provide as part of a paid offering, including charging for access, usage, subscriptions, support tiers, compute time, or hosted operation. "Commercialize" also includes monetization via advertising, sponsorship, paywalls, or bundled paid offerings where access to the Licensed Work (or a substantial portion of it) is a primary inducement of the purchase.

### 1.8 "Public Service"

"Public Service" means a service or deployment that is accessible by persons outside Your organization or outside the set of people working under Your direct control (including contractors) for Your internal purposes.

### 1.9 "Substantial Portion"

"Substantial Portion" means a portion of the Licensed Work that provides a material subset of the Licensed Work's functionality or value. Without limiting the foregoing, any portion that includes or implements (in whole or in part) a compiler, interpreter/REPL, language server, build system, package manager, dependency resolver, registry client, or official-service-compatible API shall be deemed a Substantial Portion.

### 1.10 "Primary Purpose"

"Primary Purpose" means the main intended use or marketed value of a product or service, evaluated objectively from its features, documentation, marketing, UI, pricing, and typical user behavior.

### 1.11 "Competing Use"

"Competing Use" means any of the following activities, whether directly or indirectly, including through Affiliates or contractors:

**(A) Hosted Toolchain / Dev-Tool Access (Public Service):**

Providing a Public Service that allows third parties to compile, build, test, format, lint, package, publish, execute, or analyze Pyrite/Quarry code or packages using the Licensed Work (or any Substantial Portion), including "API", "SaaS", "hosted build", "online IDE", "online REPL", or "playground" offerings, except as expressly allowed by Section 3.3.

**(B) Registry or Ecosystem Platform (Public Service):**

Creating, operating, or providing a Public Service whose Primary Purpose is to function as a package registry, package index, publishing endpoint, search API, documentation host, download-statistics service, advisories feed, dependency-graph service, compatibility-matrix service, or other ecosystem platform for Pyrite/Quarry packages, where such service is functionally similar to or substitutes for Licensor's official registry and ecosystem services.

For avoidance of doubt, a service that accepts package publishes, serves as an authoritative index, or provides public search/browse of packages is Competing Use even if free.

**(C) Selling the Toolchain or Derivatives:**

Commercializing the Licensed Work or any Derivative Work as a product, including selling binaries, paid licenses, paid subscriptions, paid feature tiers, or paid support where the Licensed Work (or a Substantial Portion) is the Primary Purpose of the paid offering.

**(D) Enabling Others' Competing Use:**

Knowingly enabling or assisting a third party to engage in Competing Use, where Your contribution is essential to that Competing Use.

### 1.12 "Non-Competing Use"

"Non-Competing Use" means any use that is not a Competing Use.

For avoidance of doubt, "Competing Use" restricts commercialization and public platform substitution of the toolchain/services themselves. It does not restrict what You build WITH the toolchain (see Section 4).

---

## 2. LICENSE GRANT (NON-COMPETING USE ONLY)

Subject to Your full compliance with this license, Licensor grants You a worldwide, non-exclusive, non-transferable, revocable license to:

- **(A)** use, reproduce, and modify the Licensed Work for Non-Competing Use;
- **(B)** create Derivative Works for Non-Competing Use; and
- **(C)** distribute copies of the Licensed Work or Derivative Works, in Source Code or Object Code form, for Non-Competing Use, provided You comply with Section 5 (Distribution Conditions).

All rights not expressly granted are reserved.

---

## 3. PROHIBITION ON COMPETING USE (PERPETUAL) + SAFE HARBORS

### 3.1 Prohibition

You may not engage in any Competing Use.

### 3.2 No Conversion

This license does not convert to an open-source license after any period of time. No "automatic relicense" is granted.

### 3.3 Limited Educational Public Demo Exception

You may operate a Public Service that allows third parties to run, compile, or experiment with Pyrite code ONLY if all of the following are true:

- **(A)** the service is strictly non-commercial: no fees, no ads, no sponsorship, and no paid tiering of any kind;
- **(B)** the service is offered solely for education, documentation, or community demonstration, and is not marketed as a general-purpose alternative to Licensor's official services;
- **(C)** the service does not provide package publishing or act as a public package registry, index, or mirror that accepts publishes;
- **(D)** the service includes clear attribution that it is third-party, not affiliated with or endorsed by Licensor; and
- **(E)** the service does not circumvent the intent of Section 3 by providing a broadly substitutive platform.

Any Commercialization of such a demo service, or any registry-like functionality, is Competing Use.

---

## 4. OUTPUT IS UNRESTRICTED + RUNTIME EXCEPTION

### 4.1 Output License

You may use, sell, license, sublicense, and distribute Output under any terms You choose, including proprietary terms, without owing Licensor fees, provided You do not violate Section 3.

### 4.2 Runtime Exception (Redistributable Components)

You may distribute Redistributable Components in Object Code form solely as part of Output (e.g., statically or dynamically linked, bundled, or embedded) to the extent reasonably necessary for recipients to run or link the Output.

This Runtime Exception is limited:

- **(A)** You may not distribute Redistributable Components on a standalone basis, or as a general-purpose runtime/SDK/package separate from Output.
- **(B)** You may not use the Runtime Exception to offer any Public Service that constitutes Competing Use.
- **(C)** You must include a copy of this license and preserve attribution notices for the Redistributable Components in a NOTICE or equivalent file shipped with the Output (or in an "About/Legal" UI where applicable).

For clarity:

- Your Output does **NOT** become subject to this license solely because it ships with Redistributable Components under this Runtime Exception.
- Recipients of your Output are permitted to use the Redistributable Components only as incorporated into, and as reasonably necessary to run or link, your Output. No broader license to the toolchain is granted thereby.

---

## 5. DISTRIBUTION CONDITIONS (LICENSED WORK / DERIVATIVES)

This Section 5 applies when You distribute the Licensed Work or any Derivative Work "as such" (for example: source distributions, toolchain binaries, forks, SDKs, libraries intended for general reuse as part of the toolchain), and does **NOT** apply to Redistributable Components distributed solely under Section 4.2 (except Section 4.2(C)).

If You distribute the Licensed Work or any Derivative Work (in Source or Object Code form) under Section 2(C), You must:

- **(A)** provide recipients a copy of this license; and
- **(B)** retain all copyright notices, license notices, and attribution notices present in the Licensed Work; and
- **(C)** clearly mark any files You modified with a notice that You changed them and the date of change; and
- **(D)** not impose additional restrictions on recipients' exercise of the rights granted by this license for Non-Competing Use (i.e., no further field-of-use restrictions beyond this license); and
- **(E)** not represent Your distribution as endorsed by, affiliated with, or authored by Licensor.

You may charge a fee to cover the cost of distribution (e.g., media, bandwidth), but You may not Commercialize the Licensed Work in a way that constitutes Competing Use.

---

## 6. PATENTS

### 6.1 Patent License from Licensor

To the extent Licensor holds patent rights that are necessarily infringed by using the Licensed Work as provided by Licensor, Licensor grants You a patent license limited to Non-Competing Use, coextensive with the copyright license in Section 2.

### 6.2 Patent Retaliation

If You initiate or fund a patent claim alleging that the Licensed Work infringes a patent, then any patent license granted to You under this license terminates immediately.

---

## 7. TRADEMARKS

This license does not grant any rights in Licensor's trademarks, service marks, or names, including "WulfHouse," "Pyrite," "Quarry," and "Forge." You may use these names only to the extent necessary to describe origin and compatibility in a truthful manner, without suggesting endorsement.

See TRADEMARK_POLICY.md for detailed trademark usage guidelines.

---

## 8. CONTRIBUTIONS (OPTIONAL INBOUND TERMS)

If You submit a Contribution to Licensor for inclusion in the Licensed Work, You grant Licensor a perpetual, worldwide, irrevocable, royalty-free license to use, reproduce, modify, distribute, and sublicense that Contribution as part of the Licensed Work under any terms Licensor chooses.

---

## 9. TERMINATION

### 9.1 Automatic Termination

Any violation of Section 3 (Competing Use) terminates this license immediately.

### 9.2 Cure for Other Breaches

For breaches other than Section 3, Licensor may terminate this license by written notice if You do not cure the breach within 30 days after receiving notice.

### 9.3 Effect of Termination

Upon termination, You must stop using and distributing the Licensed Work and Derivative Works, except that Your recipients' licenses (if granted in compliance with this license) remain in effect.

Sections 4, 6.2, 7, 9.3, 10, 11, and 12 survive termination.

---

## 10. DISCLAIMER OF WARRANTY

**THE LICENSED WORK IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, OR TITLE. YOU BEAR THE RISK OF USING IT.**

---

## 11. LIMITATION OF LIABILITY

**TO THE MAXIMUM EXTENT PERMITTED BY LAW, LICENSOR SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, REVENUE, DATA, OR GOODWILL, ARISING OUT OF OR RELATED TO THIS LICENSE OR THE LICENSED WORK, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. LICENSOR'S TOTAL LIABILITY SHALL NOT EXCEED USD $100.**

Some jurisdictions do not allow certain limitations; in that case, the limitations apply to the maximum extent permitted.

---

## 12. GOVERNING LAW AND VENUE

This license is governed by the laws of the State of Iowa, USA, excluding its conflict-of-law rules. Any dispute arising out of or relating to this license shall be brought exclusively in the state or federal courts located in Iowa, and the parties consent to personal jurisdiction and venue there.

---

## 13. MISCELLANEOUS

### 13.1 Entire Agreement

This license is the entire agreement regarding the Licensed Work.

### 13.2 Severability

If any provision is held unenforceable, the remaining provisions remain in effect, and the unenforceable provision is reformed to the minimum extent necessary to make it enforceable.

### 13.3 No Waiver

Failure to enforce any provision is not a waiver.

### 13.4 Interpretation

Headings are for convenience only. "Including" means "including without limitation."

---

**END OF LICENSE**
