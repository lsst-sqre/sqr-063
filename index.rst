:tocdepth: 1

.. sectnum::

Web security concerns
=====================

#. UWS makes extensive use of ``POST`` with the default ``application/x-www-form-urlencoded`` content type, but doesn't provide a mechanism for a client to get a form token that has to be included in all ``POST`` requests.
   This makes UWS inherently vulnerable to CSRF attacks, since cross-site ``POST`` with a content-type of ``application/x-www-form-urlencoded`` is allowed without pre-flight checks.
   See `the rules for simple requests <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#simple_requests>`__.
   In this context, a simple request is bad; you want state-changing requests to not be simple requests so that CORS preflight checks are forced.
   If simple requests cannot be avoided (if, for example, the page must be usable as the target of a form submission), there should be a mechanism to require form tokens, or some other defense against forged cross-site requests.

#. DALI requires synchronous resources be available via both ``GET`` and ``POST``.
   Implementing any resource that creates state changes in the server (such as creation of a job) via ``GET`` violates the HTTP security model and thus makes the service more vulnerable to CSRF attacks.
   See, for example, the `OWASP CSRF Prevention Cheat Sheet <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>`__: "Do not use GET requests for state changing operations."

   Not all sync requests will be state-changing, depending on the nature of the service, so it's reasonable to allow ``GET`` requests as an option, but requiring ``GET`` be supported means the only options for an implementation concerned about this risk is to not support sync requests or not follow the standard.

#. XML schema references in standards examples use ``http`` instead of ``https``.
   Depending on the nature of the XML processing library, this can create security vulnerabilities by allowing an active in-path attacker to replace the remote schema document with one that may trigger XML processor vulnerabilities.

Implementation issues
=====================

#. DALI states, "Parameter names are not case sensitive; a DAL service must treat upper-, lower-, and mixed-case parameter names as equal."
   This is a bizarre provision for a web service that makes implementing IVOA standards with comon web application frameworks unnecessarily difficult.
   For example, FastAPI's normal query and form parameter parsing with its associated automated generation of OpenAPI schemas cannot be used because they (like every other Python web framework I've used) treat parameter names as case-sensitive.
   This means that FastAPI cannot automatically impose restrictions on allowable values for parameters and automatically generate error messages.
   Parameters have to be recovered from a case-canonicalized copy of the query parameters and all the normally-automatic verification of required parameters, valid parameter names, and valid parameter values has to be tediously reimplemented manually, solely because of this requirement.

#. XML is used for all responses.
   Modern web architectures have largely abandoned XML in favor of JSON or (for high performance APIs) Protobufs.
   Generating XML is tedious and lacks first-class support in web frameworks.
   Parsing XML is similarly tedious and prone to a large number of `security issues <https://docs.python.org/3/library/xml.html#xml-vulnerabilities>`__.

#. VOTable error messages as specified in DALI do not separate the required error code from the additional details in the required ``<INFO>`` tag contents.
   Since it is using XML, this seems like a missed opportunity.
   It also doesn't provide a mechanism for separating a short error message from extended error details (such as a backtrace), even though UWS indicates this is desirable and provides its own mechanism to lift an error summary into the job list.

#. SODA requires each cutout parameter produce a separate result file, which forbids returning a single FITS file with all cutouts included (which seems like a better data model for services that can handle it).

#. SODA requires accepting invalid filter parameters for a given data ID and indicating that they are invalid solely by having the corresponding result be a ``text/plain`` document starting with an error code.
   This seems needlessly opaque and requires the client intuit that some of their requests fail by noticing the MIME type of some of the responses.
   It also creates potential confusion with SODA requests that may legitimately return a ``text/plain`` document as a valid response, and assumes structure in ``text/plain`` (which is contrary to the definition of ``text/plain``).
   None of this seems correct.
   An implementation should be able to fail the job with an error if the given parameters are inconsistent.

#. There is no specification in SODA or UWS for error replies from the async API other than job errors.
   (For example, posting an invalid time to the destruction endpoint or an invalid phase to the phase endpoint, or requesting a job that doesn't exist.)
   The HTTP status code is specified in some cases, but not the contents of the message or a clear statement that the contents don't matter.
   Should this return ``text/plain`` errors as specified for the sync API, either ``text/plain`` or VOTable per DALI, the implementor's choice as long as the HTTP status code is correct, or something else?

Standard inconsistencies
========================

#. The UWS standard for error messages says, "It is the responsibility of the implementing service to specify the form that such an error message may take."
   The SODA standard does not do this.
   Error documents are only specified for the sync API.

#. DALI says that errors may be either VOTables or plain text.
   SODA requires that errors from the sync API be plain text and doesn't allow for VOTables, but claims that it's following DALI.

#. SODA section 5.2 says, "Error codes are specified in DALI," but DALI does not specify any error codes that I could see, only a VOTable representation of errors.
   (Perhaps this refers to the brief discussion of HTTP error codes?
   If so, this is far from a full specification of possible error codes.)

Clarity issues
==============

#. There is no example of the ``jobs`` XML document returned by the UWS Job List API.
   The correct form of this document has to be reconstructed from the schema.

#. The ``isPost`` attribute of ``<uws:parameter>`` in the UWS standard is never mentioned in the text and has no ``<xs:documentation>`` element in the schema, leaving its purpose to the imagination of the reader.

#. There is no full example of a VOTable error reply in DALI.

#. SODA refers to the parameters controlling the shape of a cutout as "filtering parameters" and, in some cases, as a "filter."
   Filter is an overloaded term in astronomy so this terminology could create some confusion with, for example, optical filters.
   We used the word "stencils" instead for our implementation.

Formatting issues
=================

#. The ``job`` XML example in the UWS standard has lost all of its indentation in the HTML version of the document, making it difficult to follow.
   The UWS schema has the same issue, but at least includes a link to the same schema as a separate XML document, which will be indented properly by a modern web browser.

#. References to other IVOA standards documents are not hyperlinks, but instead are textual academic citations whose associated URLs are only listed in the References section.
   This makes it tedious to jump back and forth between related documents and find the relevant section being cited in a different document, something that's unfortunately very frequently needed to understand IVOA standards.

#. IVOA SSOAuth is not available in HTML format.
