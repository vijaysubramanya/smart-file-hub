from elasticsearch_dsl import Document, Date, Keyword, Text, Long

class FileDocument(Document):
    id = Keyword()
    name = Text(fields={'keyword': Keyword()})
    size = Long()
    content_type = Keyword()
    created_at = Date()
    extension = Keyword()

    class Index:
        name = 'files'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    def save(self, **kwargs):
        return super().save(**kwargs) 