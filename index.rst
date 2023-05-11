:tocdepth: 1

.. sectnum::

Abstract
========

Rubin Observatory has adopted an "IVOA-first" approach to APIs for the Rubin Science Platform, and are therefore implementing SODA as the protocol for providing image cutouts.
The preferred project implementation language is Python, and we have adopted `FastAPI`_ as our primary web framework.
This document collects the implementation experience of someone familiar with Python web service development but new to the IVOA standards.
It documents hurdles and roadblocks ranging from minor clarity issues to significant impediments to implementing IVOA web services using the FastAPI web framework.

.. _FastAPI: https://fastapi.tiangolo.com/

See `DMTN-208`_ for the technical architecture of our image cutout service.

.. _DMTN-208: https://dmtn-208.lsst.io/

Standards used
==============

The implementation discussed here is an image cutout service written to the SODA standard and supporting both sync and async APIs.
The versions of the IVOA standards consulted while writing this implementation were:

- `IVOA Server-side Operations for Data Access (SODA) Version 1.0 (2017-05-17) <https://ivoa.net/documents/SODA/20170517/REC-SODA-1.0.html>`__
- `Universal Worker Service Pattern (UWS) Version 1.1 (2016-10-24) <https://www.ivoa.net/documents/UWS/20161024/REC-UWS-1.1-20161024.html>`__
- `IVOA Support Interfaces (VOSI) Version 1.1 (2017-05-24) <https://www.ivoa.net/documents/VOSI/20170524/REC-VOSI-1.1.html>`__
- `Data Access Layer Interface (DALI) Version 1.1 (2017-05-17) <https://www.ivoa.net/documents/DALI/20170517/REC-DALI-1.1.html>`__
- `VOTable Format Definition (VOTable) Version 1.4 (2019-10-21) <https://www.ivoa.net/documents/VOTable/20191021/REC-VOTable-1.4-20191021.html>`__

We did not implement SSOAuth (`IVOA Single-Sign-On Profile: Authentication Mechanisms 1.01 (2008-01-24) <https://www.ivoa.net/documents/latest/SSOAuthMech.html>`__) because it does not support API bearer tokens, which is the authentication mechanism we are using for the Rubin Science Platform.
(Nor apparently does the current 2.0 draft.)

Web security concerns
=====================

POST and simple requests
------------------------

UWS makes extensive use of ``POST`` with the default ``application/x-www-form-urlencoded`` content type, but doesn't provide a mechanism for a client to get a form token that has to be included in all ``POST`` requests.
This makes UWS inherently vulnerable to CSRF attacks, since cross-site ``POST`` with a content-type of ``application/x-www-form-urlencoded`` is allowed without pre-flight checks.
See `the rules for simple requests <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#simple_requests>`__.

In this context, a simple request is bad; you want state-changing requests to not be simple requests so that CORS pre-flight checks are forced.
If simple requests cannot be avoided (if, for example, the page must be usable as the target of a form submission), there should be a mechanism to require form tokens, or some other defense against forged cross-site requests.

If client input must be in JSON or XML with an appropriate ``Content-Type`` header, it would no longer qualify as a simple request and thus force a pre-flight check.

This is primarily a concern for services that may be authenticated via cookie.
Inclusion of an ``Authorization`` header also forces pre-flight checks.

GET for state-changing operations
---------------------------------

DALI requires synchronous resources be available via both ``GET`` and ``POST``.
Implementing any resource that creates state changes in the server (such as creation of a job) via ``GET`` violates the HTTP security model and thus makes the service more vulnerable to CSRF attacks.
See, for example, the `OWASP CSRF Prevention Cheat Sheet <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>`__: "Do not use GET requests for state changing operations."

Not all sync requests will be state-changing, depending on the nature of the service, so it's reasonable to allow ``GET`` requests as an option, but requiring ``GET`` be supported means the only options for an implementation concerned about this risk is to not support sync requests or not follow the standard.

``http`` in schema references
-----------------------------

XML schema references in standards examples use ``http`` instead of ``https``.
Depending on the nature of the XML processing library, this can exacerbate security vulnerabilities by allowing an active in-path attacker to replace the remote schema document with one that may trigger XML processor vulnerabilities.

Implementation issues
=====================

Case-insensitive parameters
---------------------------

DALI states, "Parameter names are not case sensitive; a DAL service must treat upper-, lower-, and mixed-case parameter names as equal."
This is a highly unusual provision for a web service and makes implementing IVOA standards with common web application frameworks unnecessarily difficult.

For example, FastAPI's normal query and form parameter parsing with its associated automated generation of OpenAPI schemas cannot be used because they (like every other Python web framework I've used) treat parameter names as case-sensitive.
This means that FastAPI cannot automatically impose restrictions on allowable values for parameters and automatically generate error messages.
Parameters have to be recovered from a case-canonicalized copy of the query parameters and all the normally-automatic verification of required parameters, valid parameter names, and valid parameter values has to be tediously reimplemented manually, solely because of this requirement.

Implementing and testing this case-insensitivity added noticeably to the cost to the implementation.
Worse, it resulted in code that was harder to understand, debug, and maintain; made the implementation work more tedious and irritating; and made the generated OpenAPI documentation less accurate and useful.

XML
---

XML is used for all responses.
This is an older choice that was common at the time the IVOA standards were originally developed, but which has received less attention and support of late.
Newer web frameworks on both the server and client side almost always support JSON (or newer encodings such as Protobufs), but support for XML is spotty in a lot of languages and frameworks.
(Java is a notable exception.)

Similarly, new programming languages such as Go, Rust, or Julia tend to focus on good JSON support first, and while XML support may be available, it usually isn't as well-integrated into the ecosystem.
This in turn makes generating and parsing it more tedious and complex, which in turn significantly increases implementation costs.

JSON generation and parsing is normally the default, so returning XML may also require overriding defaults and manually configuring inputs and outputs to web route handlers, rather than being able to rely on the optimized default path.

XML parsing is also complex and prone to a large number of `security issues <https://docs.python.org/3/library/xml.html#xml-vulnerabilities>`__.

It is important here to distinguish between transfer formats for data and serialization formats for the web protocol.
Use of a serialization format other than XML for protocol elements doesn't necessarily imply that XML-based encodings (such as VOTable) could not be used for astronomical data, any more than use of JSON for the web protocol would imply that FITS files must be converted to JSON.
The protocol elements could use JSON or some other serialization format while still returning data streams in XML.
Choosing the best serialization format for the data itself is a beyond the scope of this tech note.

VOTable error structure
-----------------------

VOTable error messages as specified in DALI do not separate the required error code from the additional details in the required ``<INFO>`` tag contents.
Since it is using XML, this seems like a missed opportunity.
It also doesn't provide a mechanism for separating a short error message from extended error details (such as a backtrace), even though UWS indicates this is desirable and provides its own mechanism to lift an error summary into the job list.

SODA multiple cutout results
----------------------------

SODA requires each cutout filter parameter produce a separate result file, which forbids returning a single FITS file with all cutouts included (which seems like a better data model for services that can handle it).

SODA async error reporting
--------------------------

SODA requires accepting invalid filter parameters for a given ``ID`` and indicating that they are invalid solely by having the corresponding result be a ``text/plain`` document starting with an error code.
This seems needlessly opaque and requires the client intuit that some of their requests fail by noticing the MIME type of some of the responses.
It also creates potential confusion with SODA requests that may legitimately return a ``text/plain`` document as a valid response, and assumes structure in ``text/plain`` (which is contrary to the definition of ``text/plain``).
None of this seems correct.

An implementation should be able to fail the job with an error if the given parameters are inconsistent.
This would use the much clearer error handling behavior of marking the job as errored and including the error information in the job metadata.

UWS async API errors
--------------------

There is no specification in SODA or UWS for error replies from the async API other than job errors.
(For example, posting an invalid time to the destruction endpoint or an invalid phase to the phase endpoint, or requesting a job that doesn't exist.)
The HTTP status code is specified in some cases, but not the contents of the message or a clear statement that the contents don't matter.

Should this return ``text/plain`` errors as specified for the sync API, either ``text/plain`` or VOTable per DALI, the implementer's choice as long as the HTTP status code is correct, or something else?

Use of empty replies
--------------------

The ``/{jobs}/{job-id}/destruction`` and ``/{jobs}/{job-id}/quote`` UWS routes are specified as returning an empty string if the job has no destruction time or quote, respectively.
This is a poor choice of special value, since an empty body can occur by accident or error for many other reasons, such as misconfigured intermediate web servers.

Since all valid values will be ISO 8601 dates, another, less error-prone special value should be used, such as ``none``.

Mixing query and ``POST`` parameters
------------------------------------

UWS says that ``PHASE=RUN`` can be added to the query portion of the URL when creating a new job, indicating that the job should automatically be started.
This mixes query parameters with a ``POST`` body, which is unusual and generally discouraged.
Any parameters provided to a ``POST`` should be sent in the body of hte ``POST`` (and ``PHASE`` should then be reserved so that it's not used as a job parameter).

Standard inconsistencies
========================

SODA UWS errors
---------------

The UWS standard for error messages says, "It is the responsibility of the implementing service to specify the form that such an error message may take."
The SODA standard does not do this.
Error documents are only specified for the sync API.

SODA sync VOTable errors
------------------------

DALI says that errors may be either VOTables or plain text.
SODA requires that errors from the sync API be plain text and doesn't allow for VOTables, but claims that it's following DALI.

SODA error code specification
-----------------------------

SODA section 5.2 says, "Error codes are specified in DALI," but DALI does not specify any error codes that I could see, only a VOTable representation of errors.

(Perhaps this refers to the brief discussion of HTTP error codes?
If so, this is far from a full specification of possible error codes.)

Clarity issues
==============

``jobs`` XML example
--------------------

There is no example of the ``jobs`` XML document returned by the UWS Job List API.
The correct form of this document has to be reconstructed from the schema.

UWS ``isPost`` attribute
------------------------

The ``isPost`` attribute of ``<uws:parameter>`` in the UWS standard is never mentioned in the text and has no ``<xs:documentation>`` element in the schema, leaving its purpose to the imagination of the reader.

DALI VOTable error example
--------------------------

There is no full example of a VOTable error reply in DALI.

Ambiguous use of "filter"
-------------------------

SODA refers to the parameters controlling the shape of a cutout as "filtering parameters" and, in some cases, as a "filter."
Filter is an overloaded term in astronomy so this terminology could create some confusion with, for example, optical filters.
We used the word "stencils" instead for our implementation.

Formatting issues
=================

``job`` XML example
-------------------

The ``job`` XML example in the UWS standard has lost all of its indentation in the HTML version of the document, making it difficult to follow.
The UWS schema has the same issue, but at least includes a link to the same schema as a separate XML document, which will be indented properly by a modern web browser.

IVOA standard cross-references
------------------------------

References to other IVOA standards documents are not hyperlinks, but instead are textual academic citations whose associated URLs are only listed in the References section.
This makes it tedious to jump back and forth between related documents and find the relevant section being cited in a different document, something that's unfortunately very frequently needed to understand IVOA standards.

Appendix: Implementations
=========================

The (hopefully) IVOA-standard-compliant implementation of the SODA image cutout service currently in use is `vo-cutouts <https://github.com/lsst-sqre/vo-cutouts>`__.
This repository provides the service envelope and job dispatch infrastructure.
The code that generates the cutout itself is maintained separately in `image_cutout_backend <https://github.com/lsst-dm/image_cutout_backend>`__.

As an experiment to see what difference it would make to the implementation to use a protocol that is more native to FastAPI, I implemented a prototype for a modified, JSON-based protocol.
This version of the cutout service is not fully tested and is not intended to be deployed; it was written purely to test and illustrate the protocol effect on the code architecture.
That prototype can be seen at `ivoa-cutout-poc <https://github.com/lsst-sqre/ivoa-cutout-poc>`__.

David A. Wheeler's SLOCCount_ says the IVOA-standard implementation has 2,255 lines of code (not including tests), and the proof-of-concept version with a modified protocol has 1,738 lines of code (also not including tests), for a savings of a bit over 20%.

.. _SLOCCount: https://dwheeler.com/sloccount/
